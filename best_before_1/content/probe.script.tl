-- Freshness probe: for every delivered cargo unit, work out the freshness curve's adjustment (a deduction for stale or
-- spoiled cargo, a bonus for fresh cargo). With billing "ticket" (the default) it answers the engine's ticket price event
-- with 1 + the adjustment before the unit is paid, and the game pays that and shares it along the unit's chain. With
-- billing "bookings" the game pays in full and the adjustment is booked as an income entry to the player's account only:
-- the game shares a delivered unit's pay along the chain by a formula we do not know, so a booking cannot follow it. Each
-- unit also counts for its last leg's line, and lines that mostly deliver stale cargo get a "Stale Cargo" warning. At "full"
-- the log names every vehicle and line of the unit's pickup chain so the split can be studied. Log lines start with
-- "BEST_BEFORE"; tools/verify_run.py checks a run from the log.

-- The pay curve (described in settings.tl). It comes from the mod's in-game settings (the params in mod.json, which the game
-- stores in the save and lets the player change on any load) and falls back to settings.tl for a save without them.
local record Curve
	bonusPercent : number
	bonusDownToFreshness : number
	breakevenFreshness : number
	penaltyBelowFreshness : number
	penaltyPercent : number
	stored : string
	staleBelowFreshness : number -- not part of the pay: a unit below it counts as stale for the line warnings
	staleWarnings : boolean -- not part of the pay: false takes the Stale Cargo warnings down and stops counting
end

-- The file's values; settings.tl also holds logLevel, a diagnostic switch that is not part of the curve.
local record Settings
	bonusPercent : number
	bonusDownToFreshness : number
	breakevenFreshness : number
	penaltyBelowFreshness : number
	penaltyPercent : number
	logLevel : string
	staleWarnings : boolean
	staleBelowFreshness : number
	staleMonths : number
	staleMinUnits : number
	staleWarnAbove : number
	staleClearBelow : number
	billing : string
	ticketPriceProbe : string
	ticketPriceMultiplier : number
end
-- Loaded under pcall: a settings.tl the game cannot find (1.0's file list left it out) must not stop the game script. The
-- fallback mirrors settings.tl; mod.script.tl's preRunFn logs the failure.
local fallbackSettings : Settings = {
	staleWarnings = true,
	staleBelowFreshness = 0.1,
	staleMonths = 12,
	staleMinUnits = 10,
	staleWarnAbove = 0.5,
	staleClearBelow = 0.25,
	logLevel = "summary",
	billing = "ticket",
	bonusPercent = 0.2,
	bonusDownToFreshness = 0.4,
	breakevenFreshness = 0.2,
	penaltyBelowFreshness = 0.0,
	penaltyPercent = -1.0,
}
local settingsLoaded, loadedSettings = pcall(ug_require, "best_before_1::/settings.tl")
local rawSettings : Settings = settingsLoaded and (loadedSettings as Settings) or fallbackSettings

local clamp = function(value : number, low : number, high : number) : number
	return math.max(low, math.min(high, value))
end

-- The curve as used: the bonus is never negative (up to +200%), the penalty never positive (down to -100%), and the
-- three freshness points stay in the order 1 >= bonusDown >= breakeven >= penaltyBelow >= 0 whatever the source says.
local normalizeCurve = function(raw : Curve) : Curve
	local bonusDown = clamp(raw.bonusDownToFreshness, 0.0, 1.0)
	local breakeven = clamp(raw.breakevenFreshness, 0.0, bonusDown)
	return {
		bonusPercent = clamp(raw.bonusPercent, 0.0, 2.0),
		bonusDownToFreshness = bonusDown,
		breakevenFreshness = breakeven,
		penaltyBelowFreshness = clamp(raw.penaltyBelowFreshness, 0.0, breakeven),
		penaltyPercent = clamp(raw.penaltyPercent, -1.0, 0.0),
		stored = raw.stored,
		staleBelowFreshness = clamp(raw.staleBelowFreshness or 0.1, 0.0, 1.0),
		staleWarnings = raw.staleWarnings ~= false,
	}
end

local sameCurve = function(a : Curve, b : Curve) : boolean
	return a.bonusPercent == b.bonusPercent and a.bonusDownToFreshness == b.bonusDownToFreshness
		and a.breakevenFreshness == b.breakevenFreshness and a.penaltyBelowFreshness == b.penaltyBelowFreshness
		and a.penaltyPercent == b.penaltyPercent and a.stored == b.stored and a.staleBelowFreshness == b.staleBelowFreshness
		and a.staleWarnings == b.staleWarnings
end

-- How a unit that waited in a warehouse is judged. Only "corrected" is offered (not a setting); the other modes are kept in
-- curveAdjustment and the replay for later, see docs/future/stored-cargo-modes.md.
local storedMode = "corrected"

local fileCurve : Curve = normalizeCurve({
	bonusPercent = rawSettings.bonusPercent,
	bonusDownToFreshness = rawSettings.bonusDownToFreshness,
	breakevenFreshness = rawSettings.breakevenFreshness,
	penaltyBelowFreshness = rawSettings.penaltyBelowFreshness,
	penaltyPercent = rawSettings.penaltyPercent,
	stored = storedMode,
	staleBelowFreshness = rawSettings.staleBelowFreshness,
	staleWarnings = rawSettings.staleWarnings,
})

local settings : Settings = {
	logLevel = (rawSettings.logLevel == "off" or rawSettings.logLevel == "curve" or rawSettings.logLevel == "full") and rawSettings.logLevel or "summary",
	billing = rawSettings.billing == "bookings" and "bookings" or "ticket",
	ticketPriceProbe = (rawSettings.ticketPriceProbe == "observe" or rawSettings.ticketPriceProbe == "scale")
		and rawSettings.ticketPriceProbe or "off",
	ticketPriceMultiplier = clamp(rawSettings.ticketPriceMultiplier or 1.0, 0.0, 10.0),
}
-- How the curve's adjustment reaches the pay. "ticket": ticketPrice answers the engine's ticket price event with 1 + the
-- adjustment, the engine pays that and shares it along the unit's chain, and nothing is booked. "bookings": the engine pays
-- in full and update books the adjustment to the player. The test probe overrides both: "observe" answers nothing (the
-- bookings run), "scale" answers a fixed multiplier (nothing is booked).
local ticketCurve = settings.billing == "ticket" and settings.ticketPriceProbe == "off"
local ticketAnswers = ticketCurve or settings.ticketPriceProbe == "scale"
local ticketSubscribe = ticketCurve or settings.ticketPriceProbe ~= "off"
local ticketMode = settings.ticketPriceProbe ~= "off" and settings.ticketPriceProbe or (ticketCurve and "curve" or "off")
local billingMode = ticketCurve and "ticket" or (ticketAnswers and "probe" or "bookings")

local describeCurve = function(curve : Curve) : string
	return "bonusPercent=" .. tostring(curve.bonusPercent) .. " bonusDownToFreshness=" .. tostring(curve.bonusDownToFreshness)
		.. " breakevenFreshness=" .. tostring(curve.breakevenFreshness) .. " penaltyBelowFreshness=" .. tostring(curve.penaltyBelowFreshness)
		.. " penaltyPercent=" .. tostring(curve.penaltyPercent) .. " stored=" .. tostring(curve.stored)
		.. " staleBelowFreshness=" .. tostring(curve.staleBelowFreshness) .. " staleWarnings=" .. tostring(curve.staleWarnings)
end

-- Log work is skipped, not just the write: building a unit's line costs more than writing it, and runs once per delivered unit.
local logFull = settings.logLevel == "full" -- vehicle and line names, pickup chains, per-vehicle ledgers
local logUnits = settings.logLevel == "curve" or logFull -- a line per delivered unit, per adjustment sent, per balance change
local logAny = settings.logLevel ~= "off"

-- One game month of clock units (a year is 1,461,000). The "summary" totals line comes about once per game month.
local monthClock = 121750
local summaryInterval = monthClock

-- Stale line warnings (described in settings.tl), the file's values kept in range. Whether they are on is an in-game setting,
-- carried in the Curve as staleWarnings.
local record StaleSettings
	months : integer
	minUnits : integer
	warnAbove : number
	clearBelow : number
end
local staleSettings : StaleSettings = (function() : StaleSettings
	local warnAbove = clamp(rawSettings.staleWarnAbove or 0.5, 0.0, 1.0)
	return {
		months = math.floor(clamp(rawSettings.staleMonths or 12, 1, 60)),
		minUnits = math.floor(math.max(rawSettings.staleMinUnits or 10, 1)),
		warnAbove = warnAbove,
		clearBelow = clamp(rawSettings.staleClearBelow or 0.25, 0.0, warnAbove),
	}
end)()

-- The warning's notification type: stale_line_warning.res.lua registers it, stale_line_warning.script.tl draws it.
local staleNotificationType = "best_before_1::/stale_line_warning.script"

-- A deduction never takes more than this share of a unit's predicted pay. At 1.0 a full deduction on a prediction a
-- little above the real pay (it is good to about 1%) can leave the unit a hair negative.
local maxDeductionShare = 1.0

-- What the engine applies after the income function when the real value cannot be read: 0.96426, measured on Normal
-- saves at rank 3 (it is the Inflation Normal ticket price multiplier there, 1 - 2 x 0.25 / 14).
local engineFactor = 0.96426
-- The delivery limit is the game's adjusted delivery time (deliveryLimit below); this is only its fallback, as a multiple of
-- the cargo file's time. The adjusted time shrinks as the game years pass: 1.5 x in 1900, 1.4 x in 1916, about 0.75 x by 2191.
local deliverTimeMultiplier = 1.5

-- Vehicles and lines whose ledger balance is logged (every vehicle and line in an arriving unit's pickup chain, up to
-- this many).
local maxTracked = 200

-- Commands cannot be sent while the engine is delivering an event, so the handler queues the deductions and update
-- sends them. The queue lives in the game script state: module-level variables do not survive between calls.
local record PendingDeduction
	number : integer
	amount : integer -- negative for a deduction, positive for a bonus
	carrier : string
	x : number
	y : number
	z : number
end

-- One line's stale history: a ring of monthly stale shares, oldest first, and the deliveries not yet put into a bucket.
local record StaleLine
	line : Engine.Entity
	rev : integer -- the entity's first revision number when tracking started; it changes when the entity is replaced
	route : string -- the line's stops when tracking started, to see a route change
	shares : {number} -- the stale share of each month
	sources : string -- one letter per bucket: d default (0% stale, never measured), i inherited, m measured
	units : integer -- deliveries since the last measured bucket (a month under the minimum carries them on)
	stale : integer -- how many of them were stale
	warned : boolean
end

local record BookingState
	curve : Curve -- the pay curve in force, refreshed by update for handleEvent
	lastCurveNote : string
	lastCurveSource : string -- "params" or "settings.tl": where `curve` came from
	payScaleValue : number -- the pay scale read at payScaleTime, see currentPayScale
	payScaleText : string
	payScaleTime : number
	units : integer -- cargo units deducted so far
	batches : integer
	pending : {PendingDeduction}
	tracked : {Engine.Entity}
	loggedCargoTypes : {string : boolean}
	lastSnapshot : string
	lastBalance : number -- the player's balance and income total at the previous snapshot
	lastIncome : number
	lastFinance : string
	lastCompany : string
	lastPayScale : string
	logSeq : integer -- numbers the journal log lines, so a gap in the log shows dropped messages
	-- Totals since the last "summary" line.
	summaryTime : number
	sumArrivals : integer
	sumAdjusted : integer
	sumDeducted : integer
	sumBonus : integer
	-- Stale line warnings.
	staleMonth : integer -- the game month the buckets were last rolled in
	staleLines : {string : StaleLine} -- keyed by the line entity as text
	staleSent : string -- the warned lines last sent to the notifications, comma separated
	ticketPriceSubscribed : boolean -- OnCalcTicketPrice was subscribed (ticket billing or the test probe)
end

-- One entry per carrier, summed over the queue.
local record Aggregate
	carrier : string
	amount : integer
	units : integer
	x : number
	y : number
	z : number
end

-- Vehicles and lines can be sold while their cargo is still on its way, and asking the engine about a vanished entity
-- raises "Invalid entity", which would abort the whole event.
local exists = function(entity : Engine.Entity) : boolean
	return entity ~= nil and api.engine.entityExists(entity)
end

local balanceOf = function(entity : Engine.Entity) : string
	if not exists(entity) then return "gone" end
	local account : Engine.Component.Account = api.engine.getComponent(entity, api.type.ComponentType.ACCOUNT)
	return account ~= nil and tostring(account.balance) or "n/a"
end

-- The Finances tab's investment and "other" rows (construction, upkeep, subsidies), one list of per-period amounts per
-- row, as the game's own finance table computes them. Used to see what a non-income balance change was.
local describeFinance = function(player : Engine.Entity) : string
	local config = api.type.ChartConfig.new()
	config.interval = 1461000 -- one clock year of game clock units (not a calendar year)
	config.count = 4
	config.minCount = 4
	config.yStepScale = 1.0
	local ok, data = pcall(api.engine.util.finance.computeFinanceTable, player, config)
	if not ok then return "unavailable" end
	local parts : {string} = {}
	local amounts = function(values : {integer}) : string
		local text : {string} = {}
		for _, v in ipairs(values) do text[#text + 1] = tostring(v) end
		return table.concat(text, ",")
	end
	data:foreach_investment(function(key : integer, values : {integer})
		local kind = data:unfoldKey(key)
		parts[#parts + 1] = "investment[" .. tostring(kind[1]) .. "/" .. tostring(kind[2]) .. "/" .. tostring(kind[3]) .. "]=" .. amounts(values)
	end)
	data:foreach_other(function(other : JournalEntry.Other, values : {integer})
		parts[#parts + 1] = "other[" .. tostring(other) .. "]=" .. amounts(values)
	end)
	return table.concat(parts, " ")
end

-- Logs the player's balance and income figures plus the tracked ledgers, but only when something changed.
local logJournalSnapshot = function(state : GameScriptState<BookingState>, bookingState : BookingState)
	local player = api.engine.util.getPlayer()
	local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
	local ok, balance = pcall(api.engine.util.finance.getPlayersBalance, player)
	local okIncome, income = pcall(api.engine.util.finance.calcIncomeSince, -1, player)
	local parts : {string} = {
		"playerBalance=" .. tostring(ok and balance or "err"),
		"playerIncomeTotal=" .. tostring(okIncome and income or "err"),
	}
	for _, entity in ipairs(bookingState.tracked or {}) do
		parts[#parts + 1] = tostring(entity) .. "=" .. balanceOf(entity)
	end
	local snapshot = table.concat(parts, " ")
	if snapshot ~= bookingState.lastSnapshot then
		bookingState.lastSnapshot = snapshot
		bookingState.logSeq = (bookingState.logSeq or 0) + 1
		-- A balance step that is not income is a cost. Costs come with the running-cost tick, so a construction or
		-- other booking cannot be told apart from it in the balance; the finance table can, so log it when it changes.
		local nonIncomeStep : number = 0
		if ok and okIncome and bookingState.lastBalance ~= nil and bookingState.lastIncome ~= nil then
			nonIncomeStep = (balance - bookingState.lastBalance) - (income - bookingState.lastIncome)
		end
		if ok then bookingState.lastBalance = balance end
		if okIncome then bookingState.lastIncome = income end
		local finance : string = nil
		if bookingState.lastFinance == nil or nonIncomeStep ~= 0 then
			finance = describeFinance(player)
			if finance ~= bookingState.lastFinance then
				bookingState.lastFinance = finance
			else
				finance = nil
			end
		end
		state:set(bookingState)
		log.message("BEST_BEFORE journal #" .. bookingState.logSeq .. " t=" .. tostring(gameTime.gameTime) .. " " .. snapshot)
		if finance ~= nil then
			log.message("BEST_BEFORE finance after journal #" .. bookingState.logSeq .. " t=" .. tostring(gameTime.gameTime)
				.. " nonIncomeStep=" .. tostring(nonIncomeStep) .. " " .. finance)
		end
	end
end

-- The company's rank and the ticket price multiplier the game derives from it (the Inflation option cuts every vehicle's
-- income by it, so it may be the engine factor our pay prediction hard-codes). Logged at the first update and whenever it
-- changes; `expected` is the game's own multiplier for the earned rank, to compare with the stored one.
local logCompany = function(state : GameScriptState<BookingState>, bookingState : BookingState)
	-- Loaded here under pcall: a path that does not resolve must cost this log line only, never the game script (an
	-- error in the game script module repeats on every update and froze the game at 4x).
	local text = "unavailable"
	local key = text -- what the line is compared on: experience changes all the time and would log a line per update
	local loaded, util = pcall(ug_require, "::/game_mechanics/company/company_progression_util.tl")
	if loaded and util ~= nil then
		local companyProgressionUtil = util as CompanyProgressionUtil
		local ok, company = pcall(companyProgressionUtil.getCompanyProgressionState, api.engine.util.getPlayer())
		if ok and company ~= nil then
			local okExpected, expected = pcall(companyProgressionUtil.getTicketPriceMultiplierForLevel, company.potentialLevel)
			text = "level=" .. tostring(company.level) .. " potentialLevel=" .. tostring(company.potentialLevel)
				.. " experience=" .. tostring(company.experience) .. " ticketPriceMultiplier=" .. tostring(company.ticketPriceMultiplier)
				.. " expected=" .. tostring(okExpected and expected or "err")
			key = tostring(company.level) .. "/" .. tostring(company.potentialLevel) .. "/" .. tostring(company.ticketPriceMultiplier)
				.. "/" .. tostring(okExpected and expected or "err")
		end
	else
		text = "unavailable: " .. tostring(util)
		key = text
	end
	if key == bookingState.lastCompany then return end
	bookingState.lastCompany = key
	state:set(bookingState)
	local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
	log.message("BEST_BEFORE company t=" .. tostring(gameTime.gameTime) .. " " .. text)
end

-- The factor between a unit's pay from the income function's formula (price x distance) and what the game pays:
-- difficultyFactor (the Cargo Income option, passed to the income function as a captured parameter) times the company's
-- ticket price multiplier (the Inflation option, steps down with the earned rank; absent at rank 1 or Inflation None).
-- Both are read at run time under pcall and fall back to difficulty 1 and the old fixed engineFactor, so a failed read
-- costs accuracy and never the game script. `text` names each source for the log.
local record PayScale
	scale : number
	text : string
end

local readPayScale = function() : PayScale
	local difficulty : number = nil
	local okConfig, params = pcall(function() : any
		return api.res.getBaseConfig().economy.cargoIncomeScript.params
	end)
	if okConfig and params ~= nil then difficulty = (params as {string:number}).difficultyFactor end

	local multiplier : number = nil
	local loaded, util = pcall(ug_require, "::/game_mechanics/company/company_progression_util.tl")
	if loaded and util ~= nil then
		local ok, company = pcall((util as CompanyProgressionUtil).getCompanyProgressionState, api.engine.util.getPlayer())
		if ok and company ~= nil then
			multiplier = company.ticketPriceMultiplier or 1.0
		end
	end

	local text = "difficulty=" .. (difficulty ~= nil and tostring(difficulty) or "unread:1")
		.. " multiplier=" .. (multiplier ~= nil and tostring(multiplier) or "unread:" .. tostring(engineFactor))
	return { scale = (difficulty or 1.0) * (multiplier or engineFactor), text = text }
end

-- The company and the Cargo Income option change rarely (a rank-up, a setting changed on loading), so the pay scale is read
-- at most once per companyInterval of game clock and kept in the state. A clock that went back (another save loaded) reads
-- again at once. Reading also logs the payScale and company lines when they changed.
local companyInterval = 10000

local currentPayScale = function(state : GameScriptState<BookingState>, bookingState : BookingState, now : number) : PayScale
	local at = bookingState.payScaleTime
	if at ~= nil and bookingState.payScaleValue ~= nil and now >= at and now - at < companyInterval then
		return { scale = bookingState.payScaleValue, text = bookingState.payScaleText }
	end
	local pay = readPayScale()
	local text = pay.text .. " scale=" .. tostring(pay.scale)
	bookingState.payScaleValue = pay.scale
	bookingState.payScaleText = text
	bookingState.payScaleTime = now
	if logAny then
		if text ~= bookingState.lastPayScale then
			bookingState.lastPayScale = text
			log.message("BEST_BEFORE payScale t=" .. tostring(now) .. " " .. text)
		end
		logCompany(state, bookingState)
	end
	state:set(bookingState)
	return { scale = pay.scale, text = text }
end

local track = function(bookingState : BookingState, entity : Engine.Entity)
	if entity == nil then return end
	bookingState.tracked = bookingState.tracked or {}
	for _, known in ipairs(bookingState.tracked) do
		if known == entity then return end
	end
	if #bookingState.tracked < maxTracked then
		bookingState.tracked[#bookingState.tracked + 1] = entity
	end
end

-- A pickup point's carrier as the name of the journal carrier it books under.
local carrierNameOf = function(carrier : Carrier) : string
	if carrier == nil then return "OTHER" end
	local carriers = api.type.enum.Carrier
	if carrier == carriers.ROAD then return "ROAD" end
	if carrier == carriers.RAIL then return "RAIL" end
	if carrier == carriers.TRAM then return "TRAM" end
	if carrier == carriers.AIR then return "AIR" end
	if carrier == carriers.WATER then return "WATER" end
	return "OTHER"
end

local journalCarrier = function(name : string) : JournalEntry.Carrier
	local carriers = api.type.JournalEntry.Carrier
	if name == "ROAD" then return carriers.ROAD end
	if name == "RAIL" then return carriers.RAIL end
	if name == "TRAM" then return carriers.TRAM end
	if name == "AIR" then return carriers.AIR end
	if name == "WATER" then return carriers.WATER end
	return carriers.OTHER
end

local aggregate = function(queue : {PendingDeduction}) : {Aggregate}
	local result : {Aggregate} = {}
	for _, item in ipairs(queue) do
		local found = false
		for _, a in ipairs(result) do
			if a.carrier == item.carrier then
				a.amount = a.amount + item.amount
				a.units = a.units + 1
				found = true
				break
			end
		end
		if not found then
			result[#result + 1] = {
				carrier = item.carrier, amount = item.amount, units = 1, x = item.x, y = item.y, z = item.z,
			}
		end
	end
	return result
end

local nameOf = function(entity : Engine.Entity) : string
	if not exists(entity) then return "?" end
	local component : Engine.Component.Name = api.engine.getComponent(entity, api.type.ComponentType.NAME)
	return component ~= nil and component.name or "?"
end

local worldPosition = function(entity : Engine.Entity) : {number}
	if not exists(entity) then return nil end
	local construction : Engine.Component.Construction = api.engine.getComponent(entity, api.type.ComponentType.CONSTRUCTION)
	if construction == nil then
		local parent = api.engine.system.streetConnectorSystem.getConstructionEntityForSubconstruction(entity)
		if parent ~= nil and parent >= 0 and exists(parent) then
			construction = api.engine.getComponent(parent, api.type.ComponentType.CONSTRUCTION)
		end
	end
	if construction == nil then return nil end
	local m = construction.transf
	return { m[13], m[14], m[15] }
end

-- The mod's params as the game hands them to a game script: this mod's table of 1-based list positions (a slider or list
-- entry's position, not its label), keyed as in mod.json. `numbers` is not passed, so the values are rebuilt here.
-- Pay settings are positions of 5% steps: position 1 is 0% (100% for the bonus slider), so position - 1 steps of 0.05.
local readParamCurve = function() : Curve, boolean
	local ok, all = pcall(function() : {string : table}
		return api.engine.config.getModParams()
	end)
	if not ok or all == nil then return nil end
	local mine = all["best_before_1"] as {string : number}
	if mine == nil then return nil end
	local fresh, bonusDown, breakeven = mine["bestBefore.freshPay"], mine["bestBefore.bonusDownTo"], mine["bestBefore.breakeven"]
	local penaltyBelow, spoiled = mine["bestBefore.penaltyBelow"], mine["bestBefore.spoiledPay"]
	local staleBelow, warnings = mine["bestBefore.staleBelow"], mine["bestBefore.staleWarnings"]
	if fresh == nil or bonusDown == nil or breakeven == nil or penaltyBelow == nil or spoiled == nil then return nil end
	local share = function(position : number) : number -- a 5% step position as a fraction, without float noise
		return math.floor(position - 1 + 0.5) * 5 / 100
	end
	local raw : Curve = {
		bonusPercent = share(fresh), -- pay at full freshness, 100% to 200%: the bonus is the part above 100%
		bonusDownToFreshness = share(bonusDown),
		breakevenFreshness = share(breakeven),
		penaltyBelowFreshness = share(penaltyBelow),
		penaltyPercent = share(spoiled) - 1.0, -- pay when spoiled, 0% to 100%: the penalty is the part taken away
		stored = storedMode,
		staleBelowFreshness = staleBelow ~= nil and share(staleBelow) or fileCurve.staleBelowFreshness, -- 0% to 25%
		staleWarnings = fileCurve.staleWarnings,
	}
	if warnings ~= nil then raw.staleWarnings = warnings >= 2 end -- a check box: position 1 is unticked, 2 ticked
	local curve = normalizeCurve(raw)
	return curve, not sameCurve(raw, curve) -- the second value: the freshness points were out of order and were lowered
end

-- The curve in force: the in-game settings (re-read here, so a change made on loading takes effect). The game hands a
-- save that lacks them the defaults, so settings.tl's curve is only the last resort for when the game hands over no
-- settings at all. The curve is kept in the state for handleEvent, and a line is logged whenever the source or the
-- numbers change.
local activeCurve = function(state : GameScriptState<BookingState>, bookingState : BookingState) : Curve
	local curve, adjusted = readParamCurve()
	local source = "params"
	if curve == nil then
		curve = fileCurve
		source = "settings.tl"
	end
	-- Runs on every update: compare the numbers and build the log note only when they changed.
	if bookingState.curve ~= nil and bookingState.lastCurveSource == source and sameCurve(curve, bookingState.curve) then
		return curve
	end
	bookingState.lastCurveSource = source
	local note = "source=" .. source .. " " .. describeCurve(curve) .. (adjusted and " adjusted=yes" or "")
	bookingState.curve = curve
	bookingState.lastCurveNote = note
	state:set(bookingState)
	if logAny then log.message("BEST_BEFORE curveSettings " .. note) end
	return curve
end

-- The share of a unit's pay the curve adds (positive) or takes away (negative). `good` is the game's own quality flag.
local curveAdjustment = function(curve : Curve, freshness : number, good : boolean) : number
	if not good then return curve.penaltyPercent end
	if freshness < 0 then -- flagged good by the game although its age says it is past the limit: stored cargo
		if curve.stored == "neutral" then return 0.0 end
		if curve.stored == "zero" then freshness = 0.0 end
	end
	if freshness >= curve.bonusDownToFreshness then return curve.bonusPercent end
	if freshness >= curve.breakevenFreshness then
		return curve.bonusPercent * (freshness - curve.breakevenFreshness) / (curve.bonusDownToFreshness - curve.breakevenFreshness)
	end
	if freshness >= curve.penaltyBelowFreshness then
		return curve.penaltyPercent * (curve.breakevenFreshness - freshness) / (curve.breakevenFreshness - curve.penaltyBelowFreshness)
	end
	return curve.penaltyPercent
end

-- "key=value,key=value" with the keys sorted, for the one-time cargo type log line.
local describeParams = function(params : {string : number}) : string
	if params == nil then return "none" end
	local keys : {string} = {}
	for key, _ in pairs(params) do keys[#keys + 1] = key end
	table.sort(keys)
	local parts : {string} = {}
	for _, key in ipairs(keys) do parts[#parts + 1] = key .. "=" .. tostring(params[key]) end
	return table.concat(parts, ",")
end

-- One totals line per game month with units arrived since the previous one; quiet months log nothing.
local logSummary = function(state : GameScriptState<BookingState>, bookingState : BookingState)
	local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
	local now = gameTime.gameTime
	if bookingState.summaryTime == nil then
		bookingState.summaryTime = now
		state:set(bookingState)
		return
	end
	if now - bookingState.summaryTime < summaryInterval then return end
	local arrivals = bookingState.sumArrivals or 0
	if arrivals > 0 then
		local deducted = bookingState.sumDeducted or 0
		local bonus = bookingState.sumBonus or 0
		log.message("BEST_BEFORE summary t=" .. tostring(now) .. " sinceT=" .. tostring(bookingState.summaryTime)
			.. " arrivals=" .. arrivals .. " adjusted=" .. tostring(bookingState.sumAdjusted or 0)
			.. " deducted=" .. deducted .. " bonus=" .. bonus .. " net=" .. (bonus - deducted) .. " billing=" .. billingMode)
	end
	bookingState.summaryTime = now
	bookingState.sumArrivals = 0
	bookingState.sumAdjusted = 0
	bookingState.sumDeducted = 0
	bookingState.sumBonus = 0
	state:set(bookingState)
end

-- Stale line warnings. handleEvent counts each delivered unit for the line of its last leg; once a game month update rolls
-- every line's buckets, decides which lines are warned and sends the warned set to the game's Notifications game script
-- when it changed. Lines are checked at the roll: a deleted or replaced line is dropped, a line whose stops changed starts
-- over (its old history describes another route), a line that only gained or lost vehicles keeps its history.

-- The entity's first revision number (it grows when the entity is replaced), or nil when it cannot be read.
local lineRevision = function(line : Engine.Entity) : integer
	local ok, rev = pcall(api.engine.getRevision, line)
	if not ok or rev == nil then return nil end
	return rev.num[1]
end

-- The line's stops as text, or nil when the entity is not a line.
local lineRoute = function(line : Engine.Entity) : string
	local ok, route = pcall(function() : string
		local component : Engine.Component.Line = api.engine.getComponent(line, api.type.ComponentType.LINE)
		if component == nil then return nil end
		local parts : {string} = {}
		for _, stop in ipairs(component.stops) do
			parts[#parts + 1] = tostring(stop.stationGroup) .. ":" .. tostring(stop.station) .. ":" .. tostring(stop.terminal)
		end
		return table.concat(parts, ">")
	end)
	return ok and route or nil
end

local startStaleLine = function(entry : StaleLine, rev : integer, route : string)
	entry.rev = rev
	entry.route = route
	entry.shares = {}
	for i = 1, staleSettings.months do entry.shares[i] = 0.0 end
	entry.sources = string.rep("d", staleSettings.months)
	entry.units = 0
	entry.stale = 0
	entry.warned = false
end

-- Keeps the ring at staleSettings.months buckets when the setting changed: drops the oldest or adds defaults in front.
local fitStaleBuckets = function(entry : StaleLine)
	while #entry.shares > staleSettings.months do
		table.remove(entry.shares, 1)
		entry.sources = entry.sources:sub(2)
	end
	while #entry.shares < staleSettings.months do
		table.insert(entry.shares, 1, 0.0)
		entry.sources = "d" .. entry.sources
	end
end

-- Closes a month: measured when the carried deliveries reach the minimum, else the previous bucket's share again.
local rollStaleMonth = function(entry : StaleLine)
	local share = entry.shares[#entry.shares]
	local source = entry.sources:sub(-1) == "d" and "d" or "i"
	if entry.units >= staleSettings.minUnits then
		share = entry.stale / entry.units
		source = "m"
		entry.units = 0
		entry.stale = 0
	end
	table.remove(entry.shares, 1)
	entry.shares[#entry.shares + 1] = share
	entry.sources = entry.sources:sub(2) .. source
end

local averageStaleShare = function(entry : StaleLine) : number
	local sum = 0.0
	for _, share in ipairs(entry.shares) do sum = sum + share end
	return #entry.shares > 0 and sum / #entry.shares or 0.0
end

local describeStaleLine = function(key : string, entry : StaleLine) : string
	local buckets : {string} = {}
	for i, share in ipairs(entry.shares) do
		buckets[i] = entry.sources:sub(i, i) .. string.format("%.4f", share)
	end
	return "line=" .. key .. " share=" .. string.format("%.4f", averageStaleShare(entry)) .. " warned=" .. tostring(entry.warned)
		.. " units=" .. tostring(entry.units) .. " stale=" .. tostring(entry.stale) .. " buckets=" .. table.concat(buckets, ",")
		.. (logFull and (" name=\"" .. nameOf(entry.line) .. "\"") or "")
end

-- Counts one delivered unit for its line. Returns the line's key (nil when the line cannot be tracked) and whether the
-- unit was stale.
local countStaleUnit = function(bookingState : BookingState, line : Engine.Entity, now : number, freshness : number, good : boolean, curve : Curve) : string, boolean
	local stale = not good or freshness < curve.staleBelowFreshness
	if line == nil or line < 0 or not exists(line) then return nil, stale end
	local key = tostring(line)
	bookingState.staleLines = bookingState.staleLines or {}
	local entry = bookingState.staleLines[key]
	if entry == nil then
		local rev, route = lineRevision(line), lineRoute(line)
		if rev == nil or route == nil then return nil, stale end
		entry = { line = line }
		startStaleLine(entry, rev, route)
		bookingState.staleLines[key] = entry
		if logUnits then
			log.message("BEST_BEFORE staleLine t=" .. tostring(now) .. " decision=new " .. describeStaleLine(key, entry))
		end
	end
	entry.units = entry.units + 1
	if stale then entry.stale = entry.stale + 1 end
	return key, stale
end

-- Hands the full warned set to the Notifications game script: lines it no longer lists lose their warning. Sent under pcall
-- so a refused command costs the warnings, never the game script; a failed send leaves staleSent as it was, so the next
-- monthly roll sends again.
local sendStaleWarnings = function(bookingState : BookingState, keys : {string}, now : number)
	local list : {PersistentNotifications.EntitiesAndParam} = {}
	for _, key in ipairs(keys) do
		local entry = bookingState.staleLines[key]
		list[#list + 1] = {
			entities = { { entity = entry.line, revision = { num = { entry.rev, 0, 0 } } } },
			param = 1,
		}
	end
	local update : PersistentNotifications = { type = staleNotificationType, entitiesAndParam = list }
	local ok, err = pcall(function() : string
		api.cmd.sendCommand(api.cmd.makeScriptingSendEventCmd("", "Notifications", "updatePersistent", update))
		return nil
	end)
	local sent = table.concat(keys, ",")
	if ok then bookingState.staleSent = sent end
	if logAny or not ok then
		log.message("BEST_BEFORE staleWarnings t=" .. tostring(now) .. " month=" .. tostring(bookingState.staleMonth)
			.. " count=" .. tostring(#keys) .. " lines=" .. (#keys > 0 and sent or "none")
			.. (ok and "" or (" error=" .. tostring(err))))
	end
end

local updateStaleLines = function(state : GameScriptState<BookingState>, bookingState : BookingState, now : number, curve : Curve)
	if not curve.staleWarnings then
		-- Turned off: take down the warnings shown and forget the history, so turning it on again starts fresh. Tried once:
		-- a failed send is logged, not repeated on every update. This is also how a player clears the warnings before removing
		-- the mod: a save that holds one fails to load without it (docs/stale-line-warnings.md).
		local changed = bookingState.staleLines ~= nil or bookingState.staleMonth ~= nil
		if bookingState.staleSent ~= nil and bookingState.staleSent ~= "" then
			sendStaleWarnings(bookingState, {}, now)
			bookingState.staleSent = ""
			changed = true
		end
		if changed then
			bookingState.staleLines = nil
			bookingState.staleMonth = nil
			state:set(bookingState)
		end
		return
	end
	local month = math.floor(now / monthClock)
	if bookingState.staleMonth == nil or month < bookingState.staleMonth then
		bookingState.staleMonth = month
		state:set(bookingState)
		return
	end
	if month == bookingState.staleMonth then return end
	local steps = math.min(month - bookingState.staleMonth, staleSettings.months)
	bookingState.staleMonth = month
	local lines = bookingState.staleLines or {}
	local keys : {string} = {}
	for key, _ in pairs(lines) do keys[#keys + 1] = key end
	table.sort(keys)
	if logUnits then
		log.message("BEST_BEFORE staleRoll t=" .. tostring(now) .. " month=" .. tostring(month) .. " steps=" .. tostring(steps)
			.. " lines=" .. tostring(#keys) .. " months=" .. tostring(staleSettings.months) .. " minUnits=" .. tostring(staleSettings.minUnits)
			.. " staleBelow=" .. tostring(curve.staleBelowFreshness) .. " warnAbove=" .. tostring(staleSettings.warnAbove)
			.. " clearBelow=" .. tostring(staleSettings.clearBelow))
	end
	local warned : {string} = {}
	for _, key in ipairs(keys) do
		local entry = lines[key]
		local wasWarned = entry.warned
		local decision : string
		local wasReset = false
		local rev = exists(entry.line) and lineRevision(entry.line) or nil
		local route = rev ~= nil and lineRoute(entry.line) or nil
		if rev == nil or route == nil then
			decision = "gone"
			lines[key] = nil
			entry.warned = false
		elseif rev ~= entry.rev or route ~= entry.route then
			-- Which one moved is logged: whether an edit of the stops also changes the revision is not known yet.
			decision = "reset reason=" .. (rev ~= entry.rev and "revision" or "route") .. (route ~= entry.route and rev ~= entry.rev and "+route" or "")
				.. " oldRev=" .. tostring(entry.rev) .. " newRev=" .. tostring(rev) .. " oldRoute=" .. entry.route .. " newRoute=" .. route
			wasReset = true
			startStaleLine(entry, rev, route)
		else
			fitStaleBuckets(entry)
			for _ = 1, steps do rollStaleMonth(entry) end
			local share = averageStaleShare(entry)
			if not entry.warned and share > staleSettings.warnAbove then
				entry.warned = true
				decision = "warn"
			elseif entry.warned and share < staleSettings.clearBelow then
				entry.warned = false
				decision = "clear"
			else
				decision = "hold"
			end
		end
		if lines[key] ~= nil and entry.warned then warned[#warned + 1] = key end
		-- Every roll at "curve" and "full"; a warning that comes or goes, and a line reset, at any level but "off".
		if logUnits or (logAny and (entry.warned ~= wasWarned or wasReset)) then
			log.message("BEST_BEFORE staleLine t=" .. tostring(now) .. " month=" .. tostring(month) .. " decision=" .. decision
				.. " " .. describeStaleLine(key, entry))
		end
	end
	bookingState.staleLines = lines
	if table.concat(warned, ",") ~= (bookingState.staleSent or "") then
		sendStaleWarnings(bookingState, warned, now)
	end
	state:set(bookingState)
end

-- A unit's delivery limit in ms (freshness 0) and where it came from: the game's adjusted delivery time, which is what the
-- company window's Delivery Time tab shows (game_mechanics.zip: finance/finances_cargo_lifetime.tl) and what the vehicles'
-- cargo bar runs against, or deliverTimeMultiplier x the cargo file's time when that call fails.
local deliveryLimit = function(cargoTypeId : integer, fileSeconds : number) : number, string
	local ok, seconds = pcall(api.engine.util.stock.getAdjustedDeliveryTime, cargoTypeId)
	if ok and seconds ~= nil and seconds > 0 then return seconds * 1000.0, "adjusted" end
	return fileSeconds * 1000.0 * deliverTimeMultiplier, "file"
end

-- Ticket billing and the test probe. Before it pays, the engine asks every OnCalcTicketPrice subscriber for pay
-- multipliers: the param is a list of items (cargo from TransportVehicleSystem, passengers from SimEntityAtVehicleSystem),
-- each naming a vehicle, a line and the unit, and an answer {[i] = m} scales item i ({[0] = m} all of them). The base game's
-- company level and subsidies answer this way (game_mechanics.zip: company/company_growth.script.tl,
-- subventions/deliver_cargo/deliver_cargo.script.tl), and the game multiplies the answers. With ticket billing ("curve" in
-- the log) it answers 1 + the curve's adjustment for the unit's freshness, judged as the arrival handler judges it (the event
-- comes at the same clock time). The test probe's "observe" logs the items and answers nothing; "scale" answers
-- ticketPriceMultiplier for every cargo item. Nothing is written to the state here: game scripts
-- may run in one Lua state per thread, so a write from this handler could be lost; the curve is read from the in-game
-- settings directly for the same reason.
local ticketPrice = function(id : string, param : any) : {integer : number}
	if not ticketSubscribe then return nil end
	local cargo = id == "TransportVehicleSystem"
	local items = param as {CalcTicketPriceCargoEvent}
	local multipliers : {integer : number} = {}
	if cargo and settings.ticketPriceProbe == "scale" then
		for i = 1, #items do multipliers[i] = settings.ticketPriceMultiplier end
	elseif cargo and ticketCurve then
		-- Under pcall: an error here must not abort the engine's event; a unit left unanswered is paid in full.
		local ok, err = pcall(function() : string
			local curve = readParamCurve() or fileCurve
			local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
			local now = gameTime.gameTime
			for i = 1, #items do
				local unit = items[i].simEntity
				local simCargo : Engine.Component.SimCargo = exists(unit)
					and api.engine.getComponent(unit, api.type.ComponentType.SIM_CARGO) or nil
				if simCargo ~= nil then
					local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
					local limitMs = deliveryLimit(simCargo.cargoType, cargoType.timeToDeliverInSeconds)
					local ageMs = now - simCargo.pickupTime
					local freshness = limitMs > 0 and (1.0 - ageMs / limitMs) or 1.0
					local corrected = limitMs > 0 and (1.0 - (ageMs - simCargo.deliveryExtensionDuration) / limitMs) or 1.0
					local judged = curve.stored == "corrected" and corrected or freshness
					local adjustment = curveAdjustment(curve, judged, api.engine.util.cargo.isGoodQuality(unit))
					multipliers[i] = math.max(0.0, 1.0 + adjustment)
				end
			end
			return nil
		end)
		if not ok then log.message("BEST_BEFORE ticketPrice error=" .. tostring(err)) end
	end
	if logUnits then
		-- Under pcall: a logging error must not cost the answer.
		local ok, err = pcall(function() : string
			local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
			local now = gameTime.gameTime
			local sum = 0.0
			for i = 1, #items do sum = sum + items[i].basePrice end
			log.message("BEST_BEFORE ticketPrice id=" .. id .. " now=" .. tostring(now) .. " items=" .. tostring(#items)
				.. " basePriceSum=" .. tostring(sum) .. " probe=" .. ticketMode
				.. " multiplier=" .. (not cargo and "none" or settings.ticketPriceProbe == "scale" and tostring(settings.ticketPriceMultiplier)
					or ticketCurve and "curve" or "none"))
			if not cargo then return nil end
			for i = 1, #items do
				local item = items[i]
				local detail = "noSimCargo"
				local simCargo : Engine.Component.SimCargo = exists(item.simEntity)
					and api.engine.getComponent(item.simEntity, api.type.ComponentType.SIM_CARGO) or nil
				if simCargo ~= nil then
					local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
					local limitMs = deliveryLimit(simCargo.cargoType, cargoType.timeToDeliverInSeconds)
					local corrected = limitMs > 0
						and (1.0 - (now - simCargo.pickupTime - simCargo.deliveryExtensionDuration) / limitMs) or 1.0
					local points = simCargo.pickupPoints or {}
					local last = points[#points]
					detail = "cargoType=" .. tostring(simCargo.cargoType) .. " legs=" .. tostring(#points)
						.. " lastLine=" .. tostring(last and last.line) .. " lastVehicle=" .. tostring(last and last.vehicle)
						.. " good=" .. tostring(api.engine.util.cargo.isGoodQuality(item.simEntity))
						.. " corrected=" .. tostring(corrected)
				end
				if logFull and exists(item.vehicleEntity) then
					-- What the vehicle holds to be paid as it unloads (nil at the arrival event, see docs/future/discarded.md).
					local vehicle : Engine.Component.TransportVehicle
						= api.engine.getComponent(item.vehicleEntity, api.type.ComponentType.TRANSPORT_VEHICLE)
					local pending = vehicle ~= nil and vehicle.unloadPendingIncome or nil
					detail = detail .. " pending=" .. (pending ~= nil
						and (tostring(pending.amount) .. ":" .. tostring(pending.vehicleEntity) .. ":" .. tostring(pending.lineEntity)) or "nil")
				end
				log.message("BEST_BEFORE ticketItem i=" .. tostring(i) .. " unit=" .. tostring(item.simEntity)
					.. " vehicle=" .. tostring(item.vehicleEntity) .. " line=" .. tostring(item.lineEntity)
					.. " stockList=" .. tostring(item.stockListEntity) .. " basePrice=" .. tostring(item.basePrice)
					.. " distance=" .. tostring(item.distance) .. " now=" .. tostring(now)
					.. " multiplier=" .. tostring(multipliers[i] or "none") .. " " .. detail)
			end
			return nil
		end)
		if not ok then log.message("BEST_BEFORE ticketPrice error=" .. tostring(err)) end
	end
	if next(multipliers) ~= nil then return multipliers end
	return nil
end

-- The game's own figures, for the log only (under pcall: a failing call must cost the log field, not the event). The adjusted
-- delivery time is the limit deliveryLimit uses; the vehicle's average quality is the cargo bar in its window
-- (gui.zip: entity_window/vehicle/vehicle_eow.script.tl), 1 - age / adjusted time for the units still on board.
local adjustedDeliveryTime = function(cargoTypeId : integer) : string
	local ok, seconds = pcall(api.engine.util.stock.getAdjustedDeliveryTime, cargoTypeId)
	return ok and tostring(seconds) or "err"
end

local vehicleQuality = function(vehicle : Engine.Entity, cargoTypeId : integer) : string
	if not exists(vehicle) then return "gone" end
	local ok, data = pcall(api.engine.util.cargo.getCargoQualityDataForVehicle, vehicle, cargoTypeId)
	if not ok or data == nil then return "err" end
	return tostring(data.averageQuality) .. ":" .. tostring(data.countBad) .. "/" .. tostring(data.countTotal)
end

local probe : GameScript<BookingState> = {
	update = function(_userParams : table, state : GameScriptState<BookingState>, _dt : number) : any
		if not state:hasEventSubscriptions() then
			state:subscribeToEvent("OnToArriveAtDestination")
		end
		local bookingState = state:get()
		-- Saves from before the probe already have subscriptions, so this one is remembered in the state.
		if ticketSubscribe and not bookingState.ticketPriceSubscribed then
			state:subscribeToEvent("OnCalcTicketPrice")
			bookingState.ticketPriceSubscribed = true
			state:set(bookingState)
			log.message("BEST_BEFORE ticketPrice subscribed probe=" .. ticketMode)
		end
		local curve = activeCurve(state, bookingState) -- reads the in-game settings, before any unit arrives
		if logUnits then logJournalSnapshot(state, bookingState) end
		local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
		if logAny then
			currentPayScale(state, bookingState, gameTime.gameTime) -- logs the company and pay scale when they changed
			logSummary(state, bookingState)
		end
		updateStaleLines(state, bookingState, gameTime.gameTime, curve)
		if bookingState.pending == nil or #bookingState.pending == 0 then return end
		local queue = bookingState.pending
		bookingState.pending = {}
		bookingState.batches = (bookingState.batches or 0) + 1
		state:set(bookingState)
		local player = api.engine.util.getPlayer()
		for _, a in ipairs(aggregate(queue)) do
			local entry = api.type.JournalEntry.new()
			entry.amount = a.amount
			entry.time = -1 -- the engine fills in the time
			entry.category.type = api.type.JournalEntry.Type.INCOME
			entry.category.carrier = journalCarrier(a.carrier)
			local cmd = api.cmd.makeJournalBookAssetCmd(player, entry, api.type.Vec3f.new(a.x, a.y, a.z))
			if logUnits then
				log.message("BEST_BEFORE sending adjustment batch=" .. bookingState.batches .. " ledger=player"
					.. " entity=" .. tostring(player) .. " carrier=" .. a.carrier
					.. " amount=" .. tostring(a.amount) .. " units=" .. tostring(a.units))
			end
			api.cmd.sendCommand(cmd)
		end
	end,
	handleEvent = function(_userParams : table, state : GameScriptState<BookingState>, _src : string, id : string, name : string, param : any) : any
		if name == "OnCalcTicketPrice" then return ticketPrice(id, param) end
		if id ~= "SimCargoSystem" or name ~= "OnToArriveAtDestination" then return end

		local bookingState = state:get()
		bookingState.units = bookingState.units or 0
		bookingState.pending = bookingState.pending or {}
		bookingState.loggedCargoTypes = bookingState.loggedCargoTypes or {}
		local curve = activeCurve(state, bookingState) -- the settings may have changed on loading, before any update ran

		local gameTimeComponent : Engine.Component.GameTime
			= api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
		local now = gameTimeComponent.gameTime

		local pay = currentPayScale(state, bookingState, now)

		local entities = (param as table).entities as {{Engine.Entity, {Engine.Entity, integer}}}
		for _, unit in ipairs(entities) do
			local cargoEntity = unit[1]
			local good = api.engine.util.cargo.isGoodQuality(cargoEntity)
			local simCargo : Engine.Component.SimCargo = api.engine.getComponent(cargoEntity, api.type.ComponentType.SIM_CARGO)
			local detail = "no SimCargo"
			local correction = "correction=n/a"
			bookingState.sumArrivals = (bookingState.sumArrivals or 0) + 1
			if simCargo ~= nil then
				-- The unit may have changed vehicles: the first pickup point is the first leg, the last the leg that
				-- delivered it, and the carrier of the last leg is the one the deduction is booked under.
				local points = simCargo.pickupPoints or {}
				local last = points[#points]
				local carrier = last ~= nil and carrierNameOf(last.carrier) or "OTHER"
				if logUnits then
					detail = "cargoType=" .. tostring(simCargo.cargoType)
						.. " startTime=" .. tostring(simCargo.startTime)
						.. " pickupTime=" .. tostring(simCargo.pickupTime)
						.. " ext=" .. tostring(simCargo.deliveryExtensionDuration)
						.. " source=" .. tostring(simCargo.sourceEntity)
						.. " legs=" .. tostring(#points)
						.. " carrier=" .. carrier
				end
				if logFull then
					local first = points[1]
					local vehicle : Engine.Entity = first and first.vehicle
					local line : Engine.Entity = first and first.line
					local lastVehicle : Engine.Entity = last and last.vehicle
					local lastLine : Engine.Entity = last and last.line
					local chain : {string} = {}
					for _, point in ipairs(points) do
						track(bookingState, point.vehicle)
						track(bookingState, point.line)
						chain[#chain + 1] = tostring(point.vehicle) .. ":" .. tostring(point.line) .. ":" .. carrierNameOf(point.carrier)
					end
					detail = detail
						.. " vehicle=" .. tostring(vehicle)
						.. " vehicleName=\"" .. nameOf(vehicle) .. "\""
						.. " line=" .. tostring(line)
						.. " lineName=\"" .. nameOf(line) .. "\""
						.. " lastVehicle=" .. tostring(lastVehicle)
						.. " lastLine=" .. tostring(lastLine)
						.. " chain=" .. (#chain > 0 and table.concat(chain, ">") or "none")
				end

				local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
				local typeKey = tostring(simCargo.cargoType)
				if logAny and not bookingState.loggedCargoTypes[typeKey] then
					bookingState.loggedCargoTypes[typeKey] = true
					log.message("BEST_BEFORE cargoType id=" .. typeKey
						.. " timeToDeliverSeconds=" .. tostring(cargoType.timeToDeliverInSeconds)
						.. " adjustedDeliverySeconds=" .. adjustedDeliveryTime(simCargo.cargoType)
						.. " scriptRef=" .. (cargoType.scriptRef ~= nil and cargoType.scriptRef.fileName or "none")
						.. " params=" .. describeParams(cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil))
				end
				local params = cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil
				local priceFactor = params ~= nil and params.initialPrice ~= nil and params.finalPrice ~= nil
					and (params.initialPrice + (params.finalPrice - params.initialPrice) * 0.25) or nil
				local limitMs, limitFrom = deliveryLimit(simCargo.cargoType, cargoType.timeToDeliverInSeconds)
				local ageMs = now - simCargo.pickupTime
				local freshness = limitMs > 0 and (1.0 - ageMs / limitMs) or 1.0
				-- A unit that waited in a specialized warehouse has its timer paused; deliveryExtensionDuration holds that
				-- time, so the corrected age is the age minus it (checked against the game's good flag on logged runs).
				local correctedFreshness = limitMs > 0 and (1.0 - (ageMs - simCargo.deliveryExtensionDuration) / limitMs) or 1.0
				local judged = curve.stored == "corrected" and correctedFreshness or freshness
				local adjustment = curveAdjustment(curve, judged, good)
				local lastLine : Engine.Entity = last and last.line
				local staleKey : string = nil
				local staleUnit = false
				if curve.staleWarnings then staleKey, staleUnit = countStaleUnit(bookingState, lastLine, now, judged, good, curve) end
				local rate = 1.0 + adjustment
				local src = worldPosition(simCargo.sourceEntity)
				local dst = worldPosition(unit[2][1])
				local predicted = "n/a"
				local expected = "n/a"
				local deduction = 0
				local bonus = 0
				local queued = ""
				if src ~= nil and dst ~= nil and priceFactor ~= nil then
					local dx, dy, dz = dst[1] - src[1], dst[2] - src[2], dst[3] - src[3]
					local d = math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
					local income = priceFactor * d * pay.scale
					if logUnits then predicted = tostring(income) end
					local exact = math.max(adjustment * income, -maxDeductionShare * income)
					if logUnits then expected = tostring(exact) end
					-- With ticket billing the engine has already paid the adjustment; the amounts here are its estimate from
					-- the predicted pay, for the log and the summary.
					if math.abs(exact) >= 1 and (ticketCurve or not ticketAnswers) then
						local amount = exact < 0 and -math.floor(-exact + 0.5) or math.floor(exact + 0.5)
						if amount < 0 then deduction = -amount else bonus = amount end
						bookingState.sumAdjusted = (bookingState.sumAdjusted or 0) + 1
						bookingState.sumDeducted = (bookingState.sumDeducted or 0) + deduction
						bookingState.sumBonus = (bookingState.sumBonus or 0) + bonus
						if not ticketCurve then
							bookingState.units = bookingState.units + 1
							bookingState.pending[#bookingState.pending + 1] = {
								number = bookingState.units,
								amount = amount,
								carrier = carrier,
								x = dst[1], y = dst[2], z = dst[3],
							}
							if logUnits then queued = (amount < 0 and " DEDUCT#" or " BONUS#") .. bookingState.units end
						end
					end
				end
				if logUnits then
					correction = "ageMs=" .. tostring(ageMs) .. " limitMs=" .. tostring(limitMs) .. " limitFrom=" .. limitFrom
						.. " vehicleQuality=" .. vehicleQuality(last and last.vehicle, simCargo.cargoType)
						.. " freshness=" .. tostring(freshness) .. " corrected=" .. tostring(correctedFreshness) .. " rate=" .. tostring(rate)
						.. " payScale=" .. tostring(pay.scale) .. " predictedIncome=" .. predicted .. " deduction=" .. tostring(deduction)
						.. " bonus=" .. tostring(bonus) .. " staleLine=" .. (staleKey or "none") .. " staleUnit=" .. tostring(staleUnit)
						.. " expectedAdjustment=" .. expected .. " billing=" .. billingMode .. queued
				end
			end
			if logUnits then
				log.message("BEST_BEFORE arrival unit=" .. tostring(cargoEntity)
					.. " target=" .. tostring(unit[2][1])
					.. " good=" .. tostring(good)
					.. " now=" .. tostring(now)
					.. " " .. detail
					.. " " .. correction)
			end
		end
		state:set(bookingState)
	end,
}

return probe
