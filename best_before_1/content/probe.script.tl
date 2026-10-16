-- Freshness deduction probe: for every cargo unit arriving at its destination, work out how much of its pay the
-- freshness curve takes away and book that as a negative income entry to the player's account.
-- The game pays a delivered unit once, at the consumer, and shares the pay back along the chain by a formula we do not
-- know, so the deduction is not tied to a vehicle or line. The log names every vehicle and line of the unit's pickup
-- chain so the split can be studied. Log lines start with "BEST_BEFORE"; tools/verify_run.py checks a run from the log.

-- Pay curve settings, in settings.tl (the curve is described there).
local record Settings
	bonus : number
	bonusFrom : number
	breakeven : number
	penaltyFrom : number
	penalty : number
	stored : string
end
local settings = ug_require "best_before_1::/settings.tl" as Settings

-- A deduction never takes more than this share of a unit's predicted pay (the prediction is good to about 1%).
local maxDeductionShare = 0.99

-- What the engine applies after the income function (measured, cause unknown).
local engineFactor = 0.96426
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

local record BookingState
	units : integer -- cargo units deducted so far
	batches : integer
	pending : {PendingDeduction}
	tracked : {Engine.Entity}
	loggedCargoTypes : {string : boolean}
	lastSnapshot : string
	logSeq : integer -- numbers the journal log lines, so a gap in the log shows dropped messages
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

local updateCalls = 0

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
		state:set(bookingState)
		log.message("BEST_BEFORE journal #" .. bookingState.logSeq .. " t=" .. tostring(gameTime.gameTime) .. " " .. snapshot)
	end
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

-- The share of a unit's pay the curve adds (positive) or takes away (negative). `good` is the game's own quality flag.
local curveAdjustment = function(freshness : number, good : boolean) : number
	if not good then return -settings.penalty end
	if freshness < 0 then -- flagged good by the game although its age says it is past the limit: stored cargo
		if settings.stored == "neutral" then return 0.0 end
		if settings.stored == "zero" then freshness = 0.0 end
	end
	if freshness >= settings.bonusFrom then return settings.bonus end
	if freshness >= settings.breakeven then
		return settings.bonus * (freshness - settings.breakeven) / (settings.bonusFrom - settings.breakeven)
	end
	if freshness >= settings.penaltyFrom then
		return -settings.penalty * (settings.breakeven - freshness) / (settings.breakeven - settings.penaltyFrom)
	end
	return -settings.penalty
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

local probe : GameScript<BookingState> = {
	update = function(_userParams : table, state : GameScriptState<BookingState>, _dt : number) : any
		if not state:hasEventSubscriptions() then
			state:subscribeToEvent("OnToArriveAtDestination")
		end
		local bookingState = state:get()
		updateCalls = updateCalls + 1
		logJournalSnapshot(state, bookingState)
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
			log.message("BEST_BEFORE sending adjustment batch=" .. bookingState.batches .. " ledger=player"
				.. " entity=" .. tostring(player) .. " carrier=" .. a.carrier
				.. " amount=" .. tostring(a.amount) .. " units=" .. tostring(a.units))
			api.cmd.sendCommand(cmd)
		end
	end,
	handleEvent = function(_userParams : table, state : GameScriptState<BookingState>, _src : string, id : string, name : string, param : any) : any
		if id ~= "SimCargoSystem" or name ~= "OnToArriveAtDestination" then return end

		local bookingState = state:get()
		bookingState.units = bookingState.units or 0
		bookingState.pending = bookingState.pending or {}
		bookingState.loggedCargoTypes = bookingState.loggedCargoTypes or {}

		local gameTimeComponent : Engine.Component.GameTime
			= api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
		local now = gameTimeComponent.gameTime

		local entities = (param as table).entities as {{Engine.Entity, {Engine.Entity, integer}}}
		for _, unit in ipairs(entities) do
			local cargoEntity = unit[1]
			local good = api.engine.util.cargo.isGoodQuality(cargoEntity)
			local simCargo : Engine.Component.SimCargo = api.engine.getComponent(cargoEntity, api.type.ComponentType.SIM_CARGO)
			local detail = "no SimCargo"
			local correction = "correction=n/a"
			if simCargo ~= nil then
				-- The unit may have changed vehicles: the first pickup point is the first leg, the last the leg that
				-- delivered it, and the carrier of the last leg is the one the deduction is booked under.
				local points = simCargo.pickupPoints or {}
				local first = points[1]
				local last = points[#points]
				local vehicle : Engine.Entity = first and first.vehicle
				local line : Engine.Entity = first and first.line
				local lastVehicle : Engine.Entity = last and last.vehicle
				local lastLine : Engine.Entity = last and last.line
				local carrier = last ~= nil and carrierNameOf(last.carrier) or "OTHER"
				local chain : {string} = {}
				for _, point in ipairs(points) do
					track(bookingState, point.vehicle)
					track(bookingState, point.line)
					chain[#chain + 1] = tostring(point.vehicle) .. ":" .. tostring(point.line) .. ":" .. carrierNameOf(point.carrier)
				end
				detail = "cargoType=" .. tostring(simCargo.cargoType)
					.. " startTime=" .. tostring(simCargo.startTime)
					.. " pickupTime=" .. tostring(simCargo.pickupTime)
					.. " ext=" .. tostring(simCargo.deliveryExtensionDuration)
					.. " source=" .. tostring(simCargo.sourceEntity)
					.. " vehicle=" .. tostring(vehicle)
					.. " vehicleName=\"" .. nameOf(vehicle) .. "\""
					.. " line=" .. tostring(line)
					.. " lineName=\"" .. nameOf(line) .. "\""
					.. " lastVehicle=" .. tostring(lastVehicle)
					.. " lastLine=" .. tostring(lastLine)
					.. " legs=" .. tostring(#points)
					.. " chain=" .. (#chain > 0 and table.concat(chain, ">") or "none")
					.. " carrier=" .. carrier

				local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
				local typeKey = tostring(simCargo.cargoType)
				if not bookingState.loggedCargoTypes[typeKey] then
					bookingState.loggedCargoTypes[typeKey] = true
					log.message("BEST_BEFORE cargoType id=" .. typeKey
						.. " timeToDeliverSeconds=" .. tostring(cargoType.timeToDeliverInSeconds)
						.. " scriptRef=" .. (cargoType.scriptRef ~= nil and cargoType.scriptRef.fileName or "none")
						.. " params=" .. describeParams(cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil))
				end
				local params = cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil
				local priceFactor = params ~= nil and params.initialPrice ~= nil and params.finalPrice ~= nil
					and (params.initialPrice + (params.finalPrice - params.initialPrice) * 0.25) or nil
				local limitMs = cargoType.timeToDeliverInSeconds * 1000.0 * deliverTimeMultiplier
				local ageMs = now - simCargo.pickupTime
				local freshness = limitMs > 0 and (1.0 - ageMs / limitMs) or 1.0
				local adjustment = curveAdjustment(freshness, good)
				local rate = 1.0 + adjustment
				local src = worldPosition(simCargo.sourceEntity)
				local dst = worldPosition(unit[2][1])
				local predicted = "n/a"
				local deduction = 0
				local bonus = 0
				local queued = ""
				if src ~= nil and dst ~= nil and priceFactor ~= nil then
					local dx, dy, dz = dst[1] - src[1], dst[2] - src[2], dst[3] - src[3]
					local d = math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
					local income = priceFactor * d * engineFactor
					predicted = tostring(income)
					local exact = math.max(adjustment * income, -maxDeductionShare * income)
					if math.abs(exact) >= 1 then
						bookingState.units = bookingState.units + 1
						local amount = exact < 0 and -math.floor(-exact + 0.5) or math.floor(exact + 0.5)
						if amount < 0 then deduction = -amount else bonus = amount end
						bookingState.pending[#bookingState.pending + 1] = {
							number = bookingState.units,
							amount = amount,
							carrier = carrier,
							x = dst[1], y = dst[2], z = dst[3],
						}
						queued = (amount < 0 and " DEDUCT#" or " BONUS#") .. bookingState.units
					end
				end
				correction = "ageMs=" .. tostring(ageMs) .. " limitMs=" .. tostring(limitMs)
					.. " freshness=" .. tostring(freshness) .. " rate=" .. tostring(rate)
					.. " predictedIncome=" .. predicted .. " deduction=" .. tostring(deduction)
					.. " bonus=" .. tostring(bonus) .. queued
			end
			log.message("BEST_BEFORE arrival unit=" .. tostring(cargoEntity)
				.. " target=" .. tostring(unit[2][1])
				.. " good=" .. tostring(good)
				.. " now=" .. tostring(now)
				.. " " .. detail
				.. " " .. correction)
		end
		state:set(bookingState)
	end,
}

return probe
