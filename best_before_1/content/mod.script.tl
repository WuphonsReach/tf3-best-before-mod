-- Scaffold: same pay as the base game, plus logging of what the engine passes to the income function.
-- Each log line starts with "BEST_BEFORE" so it can be found in the game log.

local record BestBeforeMod
	preRunFn : function({string:any}, {{string, string}}, {string : {string : integer}}, BaseConfig)
	calcCargoIncomeFn : function({string:any}, number, {number}) : number
end

local mod : BestBeforeMod = {}

local settings = ug_require "best_before_1::/settings.tl" as {string:any}

local maxLoggedCalls = 400
local loggedCalls = 0

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
	local names : {string} = {}
	for name, _ in pairs(settings) do names[#names + 1] = name end
	table.sort(names)
	local parts : {string} = {}
	for _, name in ipairs(names) do parts[#parts + 1] = name .. "=" .. tostring(settings[name]) end
	log.message("BEST_BEFORE settings " .. table.concat(parts, " "))
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
