-- Freshness deduction probe: for every cargo unit arriving at its destination, work out how much of its pay the
-- freshness curve takes away and book that as a negative income entry to the vehicle, its line and the player.
-- Log lines start with "BEST_BEFORE"; tools/verify_run.py checks a run from the log alone.

-- Pay curve settings.
local fullPayAbove = 0.5      -- freshness at or above this pays 100%
local payAtZero = 0.3         -- pay rate at 0% freshness
local payWhenSpoiled = 0.0    -- pay rate once the unit is flagged spoiled

-- What the engine applies after the income function (measured, cause unknown).
local engineFactor = 0.96426
local deliverTimeMultiplier = 1.5

-- Test only: ships deliver fish at about 80% freshness, so no ship unit was ever deducted. Shrinking the limit for
-- WATER to a quarter puts those units near 20% freshness, so ship entries get booked.
local waterLimitScale = 0.25

-- Test run: deduct at most this many cargo units, then stop.
local maxDeductedUnits = 400

-- Vehicles and lines whose ledger balance is logged (every arriving vehicle and line, up to this many).
local maxTracked = 120

-- Commands cannot be sent while the engine is delivering an event, so the handler queues the deductions and update
-- sends them. The queue lives in the game script state: module-level variables do not survive between calls.
local record PendingDeduction
	number : integer
	amount : integer -- negative
	vehicle : Engine.Entity
	line : Engine.Entity
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
	lastSnapshot : string
	logSeq : integer -- numbers the journal log lines, so a gap in the log shows dropped messages
end

-- One entry per ledger and carrier, summed over the queue.
local record Aggregate
	ledger : string -- "vehicle", "line" or "player", for the log
	entity : Engine.Entity -- nil for the player
	carrier : string
	amount : integer
	units : integer
	x : number
	y : number
	z : number
end

local updateCalls = 0

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

-- The vehicle's carrier as the name of the journal carrier it books under.
local carrierNameOf = function(vehicle : Engine.Entity) : string
	if vehicle == nil then return "OTHER" end
	local tv : Engine.Component.TransportVehicle = api.engine.getComponent(vehicle, api.type.ComponentType.TRANSPORT_VEHICLE)
	if tv == nil then return "OTHER" end
	local carriers = api.type.enum.Carrier
	if tv.carrier == carriers.ROAD then return "ROAD" end
	if tv.carrier == carriers.RAIL then return "RAIL" end
	if tv.carrier == carriers.TRAM then return "TRAM" end
	if tv.carrier == carriers.AIR then return "AIR" end
	if tv.carrier == carriers.WATER then return "WATER" end
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
	local add = function(ledger : string, entity : Engine.Entity, item : PendingDeduction)
		for _, a in ipairs(result) do
			if a.ledger == ledger and a.entity == entity and a.carrier == item.carrier then
				a.amount = a.amount + item.amount
				a.units = a.units + 1
				return
			end
		end
		result[#result + 1] = {
			ledger = ledger, entity = entity, carrier = item.carrier,
			amount = item.amount, units = 1, x = item.x, y = item.y, z = item.z,
		}
	end
	for _, item in ipairs(queue) do
		if item.vehicle ~= nil then add("vehicle", item.vehicle, item) end
		if item.line ~= nil then add("line", item.line, item) end
		add("player", nil, item)
	end
	return result
end

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
		for _, a in ipairs(aggregate(queue)) do
			local entry = api.type.JournalEntry.new()
			entry.amount = a.amount
			entry.time = -1 -- the engine fills in the time
			entry.category.type = api.type.JournalEntry.Type.INCOME
			entry.category.carrier = journalCarrier(a.carrier)
			local payer = a.entity or api.engine.util.getPlayer()
			local cmd = api.cmd.makeJournalBookAssetCmd(payer, entry, api.type.Vec3f.new(a.x, a.y, a.z))
			log.message("BEST_BEFORE sending deduction batch=" .. bookingState.batches .. " ledger=" .. a.ledger
				.. " entity=" .. tostring(payer) .. " carrier=" .. a.carrier
				.. " amount=" .. tostring(a.amount) .. " units=" .. tostring(a.units))
			api.cmd.sendCommand(cmd)
		end
	end,
	handleEvent = function(_userParams : table, state : GameScriptState<BookingState>, _src : string, id : string, name : string, param : any) : any
		if id ~= "SimCargoSystem" or name ~= "OnToArriveAtDestination" then return end

		local bookingState = state:get()
		bookingState.units = bookingState.units or 0
		bookingState.pending = bookingState.pending or {}

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
				local pickup = simCargo.pickupPoints and simCargo.pickupPoints[1]
				local vehicle : Engine.Entity = pickup and pickup.vehicle
				local line : Engine.Entity = pickup and pickup.line
				local carrier = carrierNameOf(vehicle)
				track(bookingState, vehicle)
				track(bookingState, line)
				detail = "cargoType=" .. tostring(simCargo.cargoType)
					.. " startTime=" .. tostring(simCargo.startTime)
					.. " pickupTime=" .. tostring(simCargo.pickupTime)
					.. " source=" .. tostring(simCargo.sourceEntity)
					.. " vehicle=" .. tostring(vehicle)
					.. " vehicleName=\"" .. nameOf(vehicle) .. "\""
					.. " line=" .. tostring(line)
					.. " lineName=\"" .. nameOf(line) .. "\""
					.. " carrier=" .. carrier

				local cargoType = api.res.cargoTypeRep.get(simCargo.cargoType)
				local params = cargoType.scriptRef ~= nil and cargoType.scriptRef.params as {string:number} or nil
				local priceFactor = params ~= nil and params.initialPrice ~= nil and params.finalPrice ~= nil
					and (params.initialPrice + (params.finalPrice - params.initialPrice) * 0.25) or nil
				local limitMs = cargoType.timeToDeliverInSeconds * 1000.0 * deliverTimeMultiplier
				if carrier == "WATER" then limitMs = limitMs * waterLimitScale end
				local ageMs = now - simCargo.pickupTime
				local freshness = limitMs > 0 and (1.0 - ageMs / limitMs) or 1.0
				local rate = payRate(freshness, not good)
				local src = worldPosition(simCargo.sourceEntity)
				local dst = worldPosition(unit[2][1])
				local predicted = "n/a"
				local deduction = 0
				local queued = ""
				if src ~= nil and dst ~= nil and priceFactor ~= nil then
					local dx, dy, dz = dst[1] - src[1], dst[2] - src[2], dst[3] - src[3]
					local d = math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
					local income = priceFactor * d * engineFactor
					predicted = tostring(income)
					local exact = (1.0 - rate) * income
					if exact >= 1 and bookingState.units < maxDeductedUnits then
						bookingState.units = bookingState.units + 1
						deduction = math.floor(exact + 0.5)
						bookingState.pending[#bookingState.pending + 1] = {
							number = bookingState.units,
							amount = -deduction,
							vehicle = vehicle,
							line = line,
							carrier = carrier,
							x = dst[1], y = dst[2], z = dst[3],
						}
						queued = " DEDUCT#" .. bookingState.units
					end
				end
				correction = "ageMs=" .. tostring(ageMs) .. " limitMs=" .. tostring(limitMs)
					.. " freshness=" .. tostring(freshness) .. " rate=" .. tostring(rate)
					.. " predictedIncome=" .. predicted .. " deduction=" .. tostring(deduction) .. queued
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
