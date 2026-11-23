extends RefCounted
## Blocking for people sharing a physical space. Radio and tape voices have no scene partner.

# Each pair is ordered screen-left to screen-right. Keep the camera on the
# same side of the people throughout an exchange, including the reverse shot.
const PARTNERS := {
	"c1_flat": {"in":"steve iris"},
	"c1_pier": {"in":"steve agnes", "door":"steve lyle_copy", "bait":"steve agnes", "out":"steve pell"},
	"c1_dinner": {"in":"carmen rafa", "birthday":"mateo steve", "podcast":"tomas steve", "family":"iris luis", "out":"carmen steve"},
	"c1_escape": {"in":"steve iris", "cross":"steve iris"},
	"c2_ship": {"in":"steve iris"},
	"c3_house": {"in":"calder steve", "crossword":"calder steve", "rules":"calder steve", "mail":"calder pell", "out":"calder steve"},
	"c3_archive": {"in":"tomas steve"},
	"i1_archive": {"in":"gus archivist","reset":"gus archivist"},
	"c4_safe": {"in":"calder steve", "record":"calder steve", "match":"calder steve",
		"screens":"calder steve", "out.02":"calder rook_copy", "out.03":"steve rook_copy",
		"out.04":"steve rook_copy"},
	"c5_shack": {"in":"luis steve"},
	"c5_station": {"stephen":"steve stephen","out":"steve stephen"},
	"c6_iris": {"in":"steve iris","takes":"steve iris","hold":"steve iris","out":"steve iris"},
	"c6_jail": {"in":"pell stephen","crossword":"calder steve","exit":"calder lyle_copy"},
	"i2_nora": {"in":"nora dale","jobs":"nora lyle"},
	"c7_gate": {"in":"stephen pell","post":"pell ward","truck":"steve shaw","out":"steve wen"},
	"c7_swap": {"map":"calder stephen","tone":"calder steve"},
	"c8_lab": {"in":"wen shaw","lastpage":"wen steve"},
	"c8_beach": {"in":"saren steve","first":"saren steve","second":"saren steve","refuse":"saren steve","out":"saren steve"},
	"c8_rig": {"in":"shaw steve","path":"wen steve","out":"stephen steve"},
	"c9_gallery": {"talk":"steve nora","out":"steve nora"},
	"c9_wake": {"in":"steve nora","frank":"steve frank","helen":"steve helen","rook":"calder rook"},
	"c9_choir": {"note":"frank steve"},
	"c10_town": {"in":"nora carmen","console":"wen shaw","out":"steve agnes"},
	"c10_live": {"in":"steve stephen"},
	"epilogue": {"in":"iris nora","out":"steve nora","neighbors.01":"lyle lyle_copy",
		"neighbors.02":"pell dale","neighbors.03":"pell dale","bait.01":"agnes_original agnes",
		"bait.02":"agnes_original agnes","bait.03":"rook rook_copy","bait.04":"rook rook_copy"},
	"one_year": {"in":"steve stephen","newwind":"steve stephen"},
}

# Hand and eye work is chosen for the object people actually see in each
# room. Unlisted controls use an ordinary hand reach.
const READ := ["c2_aquarium.plan","c3_house.crossword","c3_house.rules","c3_house.mail",
	"c3_archive.paper","c3_archive.power","i1_archive.quiet","c4_safe.screens","c5_shack.notes",
	"c5_station.sleeve","c5_station.halcyon","c6_jail.mail","c7_gate.badge","c7_swap.map",
	"c8_lab.notebook","c8_lab.lastpage","c9_choir.note","c10_report.survey"]
const KNEEL := ["c1_escape.cross","c6_iris.takes","c10_town.wind"]
const OPERATE := ["c1_flat.control","c1_escape.power","i1_archive.reset","c4_escape.fault",
	"c5_shack.rig","c7_gate.truck","c5_station.automation","c6_iris.hold","i2_nora.pump","c7_swap.bus","c7_swap.tone",
	"c8_rig.rig","c9_gallery.antenna","c9_gallery.link","c10_station.route","c10_station.relay",
	"c10_town.console","c10_report.report"]
const CONVERSATIONS := {"c1_pier.door":"lyle_copy","c1_pier.bait":"agnes",
	"c1_dinner.birthday":"mateo","c1_dinner.family":"iris","c5_station.stephen":"stephen",
	"c6_jail.crossword":"calder","c6_jail.exit":"lyle_copy","i2_nora.jobs":"lyle",
	"c8_beach.first":"saren","c8_beach.second":"saren","c8_beach.refuse":"saren",
	"c9_gallery.talk":"nora","epilogue.neighbors":"pell"}
const OBSERVE := ["c1_pier.whistle","c2_ship.nora","c8_lab.props","i2_nora.patrol","c4_escape.van","c6_iris.alibi"]
const WIDE_LINES := ["c1_flat.in.04","c1_pier.bait.01","c3_house.in.01",
	"c5_station.stephen.01","c6_iris.in.02","c7_gate.in.01","c8_rig.out.01","c9_wake.in.01","epilogue.out.01"]

static func action_for(room: String, task: String, legacy_listen: Array) -> String:
	var key := task if task.contains(".") else room + "." + task
	if CONVERSATIONS.has(key):
		return "conversation"
	if key in READ:
		return "read"
	if key in KNEEL:
		return "kneel"
	if key in OPERATE:
		return "operate"
	if key in OBSERVE:
		return "observe"
	if key.get_slice(".",1) in legacy_listen or key == "c9_choir.wick":
		return "listen"
	return "reach"

static func task_partner(room: String, task: String, active: String) -> String:
	var key := task if task.contains(".") else room + "." + task
	var other: String = CONVERSATIONS.get(key,"")
	# Nora can revisit the reunion from the opposite side of the exchange.
	if other == active:
		return "steve" if room == "c9_gallery" else ""
	return other

static func dialogue_pair(room: String, line_id: String, speaker: String) -> PackedStringArray:
	var exchanges: Dictionary = PARTNERS.get(room,{})
	var pair := str(exchanges.get(line_id.trim_prefix(room+"."),exchanges.get(line_id.get_slice(".",1),"")))
	if room == "c4_safe" and line_id.begins_with("c4_safe.talk."):
		pair = "calder steve" if line_id.get_slice(".",2) == "calder" else "steve rook_copy"
	if pair.is_empty():
		return PackedStringArray()
	var names := pair.split(" ")
	return names if speaker in names else PackedStringArray()

static func pose_for(action: String) -> String:
	match action:
		"conversation": return "talk"
		"observe": return ""
		_: return action

static func hold_for(action: String) -> float:
	match action:
		"read", "listen": return 1.00
		"kneel": return 1.08
		"conversation": return .80
		"operate": return .82
		"observe": return .50
		_: return .60
