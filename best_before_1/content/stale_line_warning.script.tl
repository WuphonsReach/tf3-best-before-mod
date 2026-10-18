-- How the "Stale Cargo" warning looks: in the notification log and pop-ups, and as an icon on the line in Line & Vehicle
-- Management. probe.script.tl decides which lines are warned and hands the set to the game's Notifications game script
-- (updatePersistent); this file only draws one entry. It runs in the GUI, so it reads nothing but the line's name.

local record StaleLineParams
	entities : {EntityUtil.EntityAndRevision} -- the line
	param : integer
end

local icon = "::/game_mechanics/notifications/gui/icons/line_minus.tga"

local lineOf = function(params : StaleLineParams) : Engine.Entity
	local first = params ~= nil and params.entities ~= nil and params.entities[1] or nil
	if first == nil or not api.engine.entityExists(first.entity) then return nil end
	return first.entity
end

local data : NotificationType<StaleLineParams> = {}

data.useDataState = function(params : StaleLineParams) : NotificationGuiData
	local line = lineOf(params)
	local name : string = nil
	if line ~= nil then
		local ok, value = pcall(api.engine.util.getEntityName, line)
		if ok then name = value end
	end

	-- Like the game's own line warnings: select the line (and show it) on a click.
	local click = function(stack : boolean, dryRun : boolean) : boolean
		local target = lineOf(params)
		if target == nil then return false end
		if dryRun then return true end
		api.gui.camera.focusEntity(target)
		api.gui.fireReactEvent("selectEntity", { entity = target, stack = stack })
		return true
	end

	return {
		title = "Stale Cargo",
		icon = icon,
		lvmIcon = icon,
		iconExplainTooltip = "Most Cargo on This Line Arrives Stale",
		description = "Most cargo delivered by " .. (name ~= nil and name or "this line") .. " has arrived stale over the past"
			.. " months: below half the break-even freshness, or spoiled. Stale cargo pays less with Best Before. Faster or more"
			.. " vehicles, a shorter route or less waiting at stations will help.",
		wouldClick = function() : boolean return click(false, true) end,
		onClick = function(stack : boolean) : boolean return click(stack, false) end,
	}
end

return data
