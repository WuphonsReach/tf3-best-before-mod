-- Registers the "Stale Cargo" warning as a notification type (the game finds it by the name of
-- stale_line_warning.script with .script replaced by .res). probe.script.tl raises and clears it.
function data()
	return {
		type = "notification",
		data = {
			guiType = "Caution",
			label = "Stale Cargo (Best Before)",
			initiallyIgnoredType = false,
		},
	}
end
