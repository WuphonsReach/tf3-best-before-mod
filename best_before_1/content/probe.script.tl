-- Probe: logs every cargo unit arriving at its destination (quality flag, timestamps, vehicle, line).
-- Log lines start with "BEST_BEFORE arrival". Read-only: it does not change the game.

-- Pay curve settings (logging only for now).
local fullPayAbove = 0.5      -- freshness at or above this pays 100%
local payAtZero = 0.3         -- pay rate at 0% freshness
local payWhenSpoiled = 0.0    -- pay rate once the unit is flagged spoiled

-- What the engine applies after the income function (measured, cause unknown).
local engineFactor = 0.96426
local deliverTimeMultiplier = 1.5

local maxLoggedUnits = 2000
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

local probe : GameScript<{string:integer}> = {
	update = function(_userParams : table, state : GameScriptState<{string:integer}>, _dt : number) : any
		if not state:hasEventSubscriptions() then
			state:subscribeToEvent("OnToArriveAtDestination")
		end
	end,
	handleEvent = function(_userParams : table, _state : GameScriptState<{string:integer}>, _src : string, id : string, name : string, param : any) : any
		if id ~= "SimCargoSystem" or name ~= "OnToArriveAtDestination" then return end
		if loggedUnits >= maxLoggedUnits then return end

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
				if src ~= nil and dst ~= nil and priceFactor ~= nil then
					local dx, dy, dz = dst[1] - src[1], dst[2] - src[2], dst[3] - src[3]
					local d = math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
					local income = priceFactor * d * engineFactor
					distance = tostring(d)
					predicted = tostring(income)
					penalty = tostring((1.0 - rate) * income)
				end
				correction = "ageMs=" .. tostring(ageMs) .. " limitMs=" .. tostring(limitMs)
					.. " freshness=" .. tostring(freshness) .. " rate=" .. tostring(rate)
					.. " distance=" .. distance .. " predictedIncome=" .. predicted .. " penalty=" .. penalty
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
	end,
}

return probe
