extends HBoxContainer
## Each control is reachable by mouse and keyboard inside the investigation panel.
var options: Array
var selected := -1
var value := Button.new()
var previous := Button.new()
var following := Button.new()

func configure(label: String, choices: Array) -> void:
	options=choices
	for item: Button in [previous,value,following]:
		add_child(item)
		item.focus_mode=Control.FOCUS_ALL
	previous.text="‹"
	previous.tooltip_text="Previous setting for "+label
	previous.pressed.connect(shift.bind(-1))
	following.text="›"
	following.tooltip_text="Next setting for "+label
	following.pressed.connect(shift.bind(1))
	value.text="Choose a setting"
	value.tooltip_text=label
	value.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	value.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	value.pressed.connect(shift.bind(1))
	value.gui_input.connect(_key)

func shift(direction: int) -> void:
	selected=(0 if direction>0 else options.size()-1) if selected<0 else posmod(selected+direction, options.size())
	value.text=str(options[selected])

func _key(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_LEFT,KEY_RIGHT]:
		shift(1 if event.keycode==KEY_RIGHT else -1)
		value.accept_event()
