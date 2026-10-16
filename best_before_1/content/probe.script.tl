-- Probe: logs every cargo unit arriving at its destination (quality flag, timestamps, vehicle, line).
-- Log lines start with "BEST_BEFORE arrival". Read-only: it does not change the game.

-- Pay curve settings (logging only for now).
local fullPayAbove = 0.5      -- freshness at or above this pays 100%
local payAtZero = 0.3         -- pay rate at 0% freshness
local payWhenSpoiled = 0.0    -- pay rate once the unit is flagged spoiled

-- What the engine applies after the income function (measured, cause unknown).
local engineFactor = 0.96426
local deliverTimeMultiplier = 1.5

-- Test run: book at most this many penalties, then stop.
local maxBookings = 10

-- Commands cannot be sent while the engine is delivering an event, so the handler queues bookings and update sends them.
-- The queue lives in the game script state: module-level variables do not survive between calls.
local record PendingBooking
	number : integer
	amount : integer
	ledger : string -- "vehicle", "line" or "player", for the log
	target : Engine.Entity -- entity to book to instead of the player (nil = player account)
	x : number
	y : number
	z : number
end
local updateCalls = 0

local record BookingState
	bookings : integer
	pending : {PendingBooking}
	tracked : {Engine.Entity} -- vehicles and lines whose ledger balance is logged
	lastSnapshot : string
	logSeq : integer -- numbers the journal log lines, so a gap in the log shows dropped messages
end

-- Test of whether vehicle and line bookings ever reach the player's account (a slow roll-up): book only to the
-- vehicle and the line and watch the player's own journal figures in the log.
local bookToPlayer = false
local maxTracked = 8

local balanceOf = function(entity : Engine.Entity) : string
	local account : Engine.Component.Account = api.engine.getComponent(entity, api.type.ComponentType.ACCOUNT)
	return account ~= nil and tostring(account.balance) or "n/a"
end

-- Logs the player's balance and income figures plus the tracked ledgers, but only when something changed.
local logJournalSnapshot = function(state : GameScriptState<BookingState>, bookingState : BookingState)
	local player = api.engine.util.getPlayer()
	local gameTime : Engine.Component.GameTime = api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
	local ok, balance = pcall(api.engine.util.finance.getPlayersBalance, player)
	local okIncome, income = pcall(api.engine.util.finance.calcIncomeSince, -1, player)
	local okLast, lastTime = pcall(api.engine.util.finance.getLastIncomeTime, player)
	local parts : {string} = {
		"playerBalance=" .. tostring(ok and balance or "err"),
		"playerAccountComponent=" .. balanceOf(player),
		"playerIncomeTotal=" .. tostring(okIncome and income or "err"),
		"lastIncomeTime=" .. tostring(okLast and lastTime or "err"),
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

-- Module-level counters like this one do not survive between calls (each call may run in a fresh environment), so
-- this cap is only loose; the real cap is maxBookings, kept in the game script state.
local maxLoggedUnits = 100000
local loggedUnits = 0

local nameOf = function(entity : Engine.Entity) : string
	if entity == nil then return "?" end
	local component : Engine.Component.Name = api.engine.getComponent(entity, api.type.ComponentType.NAME)
	return component ~= nil and component.name or "?"
end

local worldPosition = function(entity : Engine.Entity) : {number}
	if entity == nil then return nil end
	local construction : Engine.Component.Construction = api.engine.getComponent(entity, api.type.ComponentType.CONSTRUCTION)
	if construction == nil then
		local parent = api.engine.system.streetConnectorSystem.getConstructionEntityForSubconstruction(entity)
		if parent ~= nil and parent >= 0 then
			construction = api.engine.getComponent(parent, api.type.ComponentType.CONSTRUCTION)
		end
	end
	if construction == nil then return nil end
	local m = construction.transf
	return { m[13], m[14], m[15] }
end

local payRate = function(freshness : number, spoiled : boolean) : number
	if spoiled then return payWhenSpoiled end
	if freshness >= fullPayAbove then return 1.0 end
	local f = math.max(freshness, 0.0)
	return payAtZero + (1.0 - payAtZero) * f / fullPayAbove
end

-- Discovery: which logbook names do a vehicle and its line carry? (read-only, first few arrivals only)
local maxLogbookDumps = 4
local logbookDumps = 0

local dumpLogbook = function(label : string, entity : Engine.Entity)
	if entity == nil then return end
	local logbook : Engine.Component.LogBook = api.engine.getComponent(entity, api.type.ComponentType.LOG_BOOK)
	if logbook == nil then
		log.message("BEST_BEFORE logbook " .. label .. " entity=" .. tostring(entity) .. " has no LOG_BOOK component")
		return
	end
	local account : Engine.Component.Account = api.engine.getComponent(entity, api.type.ComponentType.ACCOUNT)
	log.message("BEST_BEFORE account " .. label .. " entity=" .. tostring(entity)
		.. (account ~= nil and (" balance=" .. tostring(account.balance)) or " has no ACCOUNT component"))
	local parts : {string} = {}
	for logName, _ in pairs(logbook.name2log) do
		local ok, recent = pcall(api.engine.util.logbook.getLogValueMostRecent, entity, logName)
		local okYear, perYear = pcall(api.engine.util.logbook.getLogValuePerYear, entity, logName)
		parts[#parts + 1] = logName .. "=recent:" .. tostring(ok and recent or "err") .. "/year:" .. tostring(okYear and perYear or "err")
	end
	log.message("BEST_BEFORE logbook " .. label .. " entity=" .. tostring(entity) .. " names: " .. table.concat(parts, "; "))
end

local probe : GameScript<BookingState> = {
	update = function(_userParams : table, state : GameScriptState<BookingState>, _dt : number) : any
		if not state:hasEventSubscriptions() then
			state:subscribeToEvent("OnToArriveAtDestination")
		end
		local bookingState = state:get()
		updateCalls = updateCalls + 1
		if updateCalls <= 3 or (bookingState.pending ~= nil and #bookingState.pending > 0) then
			log.message("BEST_BEFORE update call " .. updateCalls .. " bookings=" .. tostring(bookingState.bookings)
				.. " pending=" .. tostring(bookingState.pending and #bookingState.pending))
		end
		logJournalSnapshot(state, bookingState)
		if bookingState.pending == nil or #bookingState.pending == 0 then return end
		local queue = bookingState.pending
		bookingState.pending = {}
		state:set(bookingState)
		for _, booking in ipairs(queue) do
			local entry = api.type.JournalEntry.new()
			entry.amount = booking.amount
			entry.time = -1 -- the engine fills in the time
			entry.category.type = api.type.JournalEntry.Type.INCOME
			entry.category.carrier = api.type.JournalEntry.Carrier.ROAD
			local payer = booking.target or api.engine.util.getPlayer()
			local cmd = api.cmd.makeJournalBookAssetCmd(payer, entry, api.type.Vec3f.new(booking.x, booking.y, booking.z))
			log.message("BEST_BEFORE sending booking " .. booking.number .. " ledger=" .. booking.ledger
				.. " amount=" .. tostring(booking.amount) .. " payer=" .. tostring(payer))
			api.cmd.sendCommand(cmd)
		end
	end,
	handleEvent = function(_userParams : table, state : GameScriptState<BookingState>, _src : string, id : string, name : string, param : any) : any
		if id ~= "SimCargoSystem" or name ~= "OnToArriveAtDestination" then return end
		if loggedUnits >= maxLoggedUnits then return end

		local bookingState = state:get()
		bookingState.bookings = bookingState.bookings or 0
		bookingState.pending = bookingState.pending or {}

		local gameTimeComponent : Engine.Component.GameTime
			= api.engine.getComponent(api.engine.util.getWorld(), api.type.ComponentType.GAME_TIME)
		local now = gameTimeComponent.gameTime

		local entities = (param as table).entities as {{Engine.Entity, {Engine.Entity, integer}}}
		for _, unit in ipairs(entities) do
			loggedUnits = loggedUnits + 1
			local cargoEntity = unit[1]
			local good = api.engine.util.cargo.isGoodQuality(cargoEntity)
			local simCargo : Engine.Component.SimCargo = api.engine.getComponent(cargoEntity, api.type.ComponentType.SIM_CARGO)
			local pending = "n/a"
			local detail = "no SimCargo"
			if simCargo ~= nil then
				local pickup = simCargo.pickupPoints and simCargo.pickupPoints[1]
				detail = "cargoType=" .. tostring(simCargo.cargoType)
					.. " startTime=" .. tostring(simCargo.startTime)
					.. " pickupTime=" .. tostring(simCargo.pickupTime)
					.. " extension=" .. tostring(simCargo.deliveryExtensionDuration)
					.. " source=" .. tostring(simCargo.sourceEntity)
					.. " vehicle=" .. tostring(pickup and pickup.vehicle)
					.. " vehicleName=\"" .. nameOf(pickup and pickup.vehicle) .. "\""
					.. " line=" .. tostring(pickup and pickup.line)
					.. " lineName=\"" .. nameOf(pickup and pickup.line) .. "\""
				if pickup and logbookDumps < maxLogbookDumps then
					logbookDumps = logbookDumps + 1
					dumpLogbook("vehicle", pickup.vehicle)
					dumpLogbook("line", pickup.line)
				end
				if pickup and pickup.vehicle then
					local tv : Engine.Component.TransportVehicle = api.engine.getComponent(pickup.vehicle, api.type.ComponentType.TRANSPORT_VEHICLE)
					if tv ~= nil and tv.unloadPendingIncome ~= nil then
						pending = tostring(tv.unloadPendingIncome.amount)
					end
				end
			end
			local correction = "correction=n/a"
			if simCargo ~= nil then
				local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
				local params = cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil
				local priceFactor = params ~= nil and params.initialPrice ~= nil and params.finalPrice ~= nil
					and (params.initialPrice + (params.finalPrice - params.initialPrice) * 0.25) or nil
				local limitMs = cargoType.timeToDeliverInSeconds * 1000.0 * deliverTimeMultiplier
				local ageMs = now - simCargo.pickupTime
				local freshness = limitMs > 0 and (1.0 - ageMs / limitMs) or 1.0
				local rate = payRate(freshness, not good)
				local src = worldPosition(simCargo.sourceEntity)
				local dst = worldPosition(unit[2][1])
				local predicted = "n/a"
				local penalty = "n/a"
				local distance = "n/a"
				local booked = ""
				if src ~= nil and dst ~= nil and priceFactor ~= nil then
					local dx, dy, dz = dst[1] - src[1], dst[2] - src[2], dst[3] - src[3]
					local d = math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
					local income = priceFactor * d * engineFactor
					distance = tostring(d)
					predicted = tostring(income)
					local penaltyAmount = (1.0 - rate) * income
					penalty = tostring(penaltyAmount)
					if penaltyAmount >= 1 and bookingState.bookings < maxBookings then
						bookingState.bookings = bookingState.bookings + 1
						-- One penalty is booked to each ledger the real pay lands in: the vehicle, the line and the player.
						local bookPickup = simCargo.pickupPoints and simCargo.pickupPoints[1]
						local amount = -math.floor(penaltyAmount + 0.5)
						local ledgers : {{string, Engine.Entity}} = {}
						if bookPickup ~= nil then
							ledgers[#ledgers + 1] = { "vehicle", bookPickup.vehicle }
							ledgers[#ledgers + 1] = { "line", bookPickup.line }
						end
						if bookToPlayer then ledgers[#ledgers + 1] = { "player", nil } end
						for _, ledger in ipairs(ledgers) do
							bookingState.pending[#bookingState.pending + 1] = {
								number = bookingState.bookings,
								amount = amount,
								ledger = ledger[1],
								target = ledger[2],
								x = dst[1], y = dst[2], z = dst[3],
							}
							if ledger[2] ~= nil then
								bookingState.tracked = bookingState.tracked or {}
								local known = false
								for _, e in ipairs(bookingState.tracked) do if e == ledger[2] then known = true end end
								if not known and #bookingState.tracked < maxTracked then
									bookingState.tracked[#bookingState.tracked + 1] = ledger[2]
								end
							end
						end
						booked = " BOOKED#" .. bookingState.bookings
					end
				end
				correction = "ageMs=" .. tostring(ageMs) .. " limitMs=" .. tostring(limitMs)
					.. " freshness=" .. tostring(freshness) .. " rate=" .. tostring(rate)
					.. " distance=" .. distance .. " predictedIncome=" .. predicted .. " penalty=" .. penalty .. booked
			end
			log.message("BEST_BEFORE arrival unit=" .. tostring(cargoEntity)
				.. " target=" .. tostring(unit[2][1])
				.. " targetExtra=" .. tostring(unit[2][2])
				.. " vehiclePendingIncome=" .. pending
				.. " good=" .. tostring(good)
				.. " now=" .. tostring(now)
				.. " " .. detail
				.. " " .. correction)
		end
		state:set(bookingState)
	end,
}

return probe
