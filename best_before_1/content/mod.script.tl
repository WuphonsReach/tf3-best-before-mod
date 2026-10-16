-- Scaffold: same pay as the base game, plus logging of what the engine passes to the income function.
-- Each log line starts with "BEST_BEFORE" so it can be found in the game log.

local record BestBeforeMod
	preRunFn : function({string:any}, {{string, string}}, {string : {string : integer}}, BaseConfig)
	calcCargoIncomeFn : function({string:any}, number, {number}) : number
	postRunFn : function({string:any})
	priceFn : function(...: any) : number
end

local mod : BestBeforeMod = {}

local maxLoggedCalls = 400
local loggedCalls = 0

local maxLoggedPriceCalls = 300
local loggedPriceCalls = 0

local travelDistance = function(posDifference : {number}) : number
	local dx, dy, dz = posDifference[1], posDifference[2], posDifference[3]
	return math.sqrt(dx * dx + dy * dy + dz * dz) + 8. * math.max(dz, 0.)
end

local describe = function(value : any) : string
	if type(value) == "table" then
		local parts : {string} = {}
		for k, v in pairs(value as {any:any}) do
			parts[#parts + 1] = tostring(k) .. "=" .. tostring(v)
		end
		return "{" .. table.concat(parts, ", ") .. "}"
	end
	return tostring(value)
end

mod.preRunFn = function(_captureParams : {string:any}, _configDict : {{string, string}}, _allModParams : {string : {string : integer}}, baseConfig : BaseConfig)
	baseConfig.economy.cargoIncomeScript.fileName = "best_before_1::/mod.script@calcCargoIncomeFn"
	log.message("BEST_BEFORE preRunFn: cargoIncomeScript replaced")
end

mod.postRunFn = function(_captureParams : {string:any})
	for id, name in pairs(api.res.cargoTypeRep.getAll()) do
		local cargoType = api.res.cargoTypeRep.getAsTable(id)
		local ref = cargoType.scriptRef
		local current = ref ~= nil and ref.fileName or "none"
		log.message("BEST_BEFORE cargo type " .. tostring(id) .. " " .. tostring(name) .. " scriptRef=" .. current)
		if ref ~= nil and string.find(current, "constantFn", 1, true) then
			ref.fileName = "best_before_1::/mod.script@priceFn"
			api.res.cargoTypeRep.setAsTable(id, cargoType)
		end
	end
end

-- Same value as the base constantFn; logs every argument the engine passes so we can see what the time argument holds.
mod.priceFn = function(...: any) : number
	local args : {any} = {...}
	local params : {string:any} = nil
	local parts : {string} = {}
	for i = 1, select("#", ...) do
		parts[#parts + 1] = "arg" .. i .. "=" .. describe(args[i])
		if params == nil and type(args[i]) == "table" then
			params = args[i] as {string:any}
		end
	end
	if loggedPriceCalls < maxLoggedPriceCalls then
		loggedPriceCalls = loggedPriceCalls + 1
		log.message("BEST_BEFORE price call " .. loggedPriceCalls .. " " .. table.concat(parts, " "))
	end
	if params ~= nil and params.initialPrice ~= nil and params.finalPrice ~= nil then
		local initialPrice = params.initialPrice as number
		local finalPrice = params.finalPrice as number
		return initialPrice + (finalPrice - initialPrice) * 0.25
	end
	return 6
end

mod.calcCargoIncomeFn = function(captureParams : {string:any}, incomeFactor : number, posDifference : {number}) : number
	local income = incomeFactor * (captureParams.difficultyFactor as number) * travelDistance(posDifference)
	if loggedCalls < maxLoggedCalls then
		loggedCalls = loggedCalls + 1
		log.message("BEST_BEFORE income call " .. loggedCalls
			.. " captureParams=" .. describe(captureParams)
			.. " incomeFactor=" .. tostring(incomeFactor)
			.. " posDifference=" .. describe(posDifference)
			.. " result=" .. tostring(income))
	end
	return income
end

return mod
