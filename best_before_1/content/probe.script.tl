-- Probe: logs every cargo unit arriving at its destination (quality flag, timestamps, vehicle, line).
-- Log lines start with "BEST_BEFORE arrival". Read-only: it does not change the game.

local maxLoggedUnits = 2000
local loggedUnits = 0

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
					.. " line=" .. tostring(pickup and pickup.line)
				if pickup and pickup.vehicle then
					local tv : Engine.Component.TransportVehicle = api.engine.getComponent(pickup.vehicle, api.type.ComponentType.TRANSPORT_VEHICLE)
					if tv ~= nil and tv.unloadPendingIncome ~= nil then
						pending = tostring(tv.unloadPendingIncome.amount)
					end
				end
			end
			log.message("BEST_BEFORE arrival unit=" .. tostring(cargoEntity)
				.. " target=" .. tostring(unit[2][1])
				.. " targetExtra=" .. tostring(unit[2][2])
				.. " vehiclePendingIncome=" .. pending
				.. " good=" .. tostring(good)
				.. " now=" .. tostring(now)
				.. " " .. detail)
		end
	end,
}

return probe
