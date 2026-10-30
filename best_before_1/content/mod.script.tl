-- Load-time script: logs the version, settings.tl's numbers and the in-game settings of each load. With incomeLogging on in
-- settings.tl (test only) it also replaces the game's cargo income function with a copy of the base formula that logs what the
-- engine passes in (pay unchanged); off, as shipped, the mod replaces nothing, since only one mod can replace that function.
-- Each log line starts with "BEST_BEFORE" so it can be found in the game log.

local record BestBeforeMod
	preRunFn : function({string:any}, {{string, string}}, {string : {string : integer}}, BaseConfig)
	calcCargoIncomeFn : function({string:any}, number, {number}) : number
end

local mod : BestBeforeMod = {}

-- settings.tl is loaded under pcall: if the game cannot find it (a mod file list that leaves it out did exactly that in 1.0), the
-- mod runs on these numbers, which mirror settings.tl, instead of the game refusing to start. preRunFn logs when that happens.
local fallbackSettings : {string:any} = {
	logLevel = "summary",
	incomeLogging = false,
	bonusPercent = 0.2,
	bonusDownToFreshness = 0.4,
	breakevenFreshness = 0.2,
	penaltyBelowFreshness = 0.0,
	penaltyPercent = -1.0,
}
local settingsLoaded, loadedSettings = pcall(ug_require, "best_before_1::/settings.tl")
local settings : {string:any} = settingsLoaded and (loadedSettings as {string:any}) or fallbackSettings

-- Set it to the release number in the release commit, equal to that CHANGELOG.md entry; between releases it is the next number with "-dev" (the changelog lists its changes under "not released").
local modVersion = "1.4-dev"

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

mod.preRunFn = function(_captureParams : {string:any}, _configDict : {{string, string}}, allModParams : {string : {string : integer}}, baseConfig : BaseConfig)
	-- Which copy loaded: the published mod and the staging_area copy share the id best_before_1, and the game does not log which
	-- one it picked. modVersion is the number in the changelog; the script's own path is only the virtual best_before_1::/ one.
	log.message("BEST_BEFORE version " .. modVersion)
	if settings.incomeLogging == true then
		baseConfig.economy.cargoIncomeScript.fileName = "best_before_1::/mod.script@calcCargoIncomeFn"
		log.message("BEST_BEFORE preRunFn: cargoIncomeScript replaced (incomeLogging is on in settings.tl)")
	else
		log.message("BEST_BEFORE preRunFn: cargoIncomeScript left to the game")
	end
	if not settingsLoaded then
		log.message("BEST_BEFORE settings.tl could not be loaded (" .. tostring(loadedSettings) .. "); running on the built-in defaults")
	end
	local names : {string} = {}
	for name, _ in pairs(settings) do names[#names + 1] = name end
	table.sort(names)
	local parts : {string} = {}
	for _, name in ipairs(names) do parts[#parts + 1] = name .. "=" .. tostring(settings[name]) end
	-- The numbers are settings.tl's: its curve is only the fallback. The curve in force is in the loadParams line below and in the
	-- curveSettings lines, and each staleRoll line says the freshness a unit has to fall below to count as stale.
	log.message("BEST_BEFORE settings (settings.tl; its curve is only the fallback) " .. table.concat(parts, " "))
	local level = settings.logLevel
	if level ~= "off" and level ~= "summary" and level ~= "curve" and level ~= "full" then
		log.message("BEST_BEFORE settings logLevel=" .. tostring(level) .. " is not off, summary, curve or full and will count as summary")
	end
	-- The in-game settings this load starts with, as the 1-based list positions the game stores (the keys without the
	-- "bestBefore." prefix). One line per load, so tools/replay_curve.py and tools/extract_run.py know the curve a run was
	-- played on. The probe's curveSettings line is logged only when the curve differs from the one stored in the save.
	local okParams, paramsText = pcall(function() : string
		local mine = allModParams["best_before_1"]
		if mine == nil then return "none" end
		local keys : {string} = {}
		for key, _ in pairs(mine) do keys[#keys + 1] = key end
		table.sort(keys)
		local pairsText : {string} = {}
		for _, key in ipairs(keys) do pairsText[#pairsText + 1] = (string.gsub(key, "^bestBefore%.", "")) .. "=" .. tostring(mine[key]) end
		return table.concat(pairsText, " ")
	end)
	log.message("BEST_BEFORE loadParams " .. (okParams and paramsText or ("error: " .. tostring(paramsText))))
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
