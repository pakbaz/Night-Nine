class_name NightTapeRecording
extends RefCounted
## Holds two complete cassette captures and aligns Sunday against Saturday.
const BIN_FRAMES := 64
var pcm_a := PackedByteArray()
var pcm_b := PackedByteArray()
var samples_a := PackedFloat32Array()
var samples_b := PackedFloat32Array()
var peaks_a := PackedVector2Array()
var peaks_b := PackedVector2Array()
var segments_a: Array = []
var segments_b: Array = []
var rate := 48000
var expected_offset := -0.35
var alignment_required := true
var label_a := "SATURDAY"
var label_b := "SUNDAY"
var timeline_start := -0.8
var timeline_end := 10.25
var error := ""

func configure(saturday: AudioStreamWAV, sunday: AudioStreamWAV, metadata: Dictionary) -> bool:
	var tapes: Dictionary = metadata.get("tapes", {})
	if not tapes.has("saturday") or not tapes.has("sunday"):
		error = "The cassette segment notes are unavailable."
		return false
	var first: Dictionary = tapes.saturday
	var second: Dictionary = tapes.sunday
	var options := {
		"segments_a": first.get("segments", []),
		"segments_b": second.get("segments", []),
		"seconds_a": first.get("seconds", 0.0),
		"seconds_b": second.get("seconds", 0.0),
		"anchor_a": "Ident",
		"anchor_b": "Ident",
		"label_a": "SATURDAY",
		"label_b": "SUNDAY"
	}
	return configure_pair(saturday, sunday, options)

func configure_pair(first: AudioStreamWAV, second: AudioStreamWAV, metadata: Dictionary = {}) -> bool:
	_clear()
	if not _valid_stream(first) or not _valid_stream(second):
		error = "This comparison requires both original mono PCM recordings."
		return false
	if first.mix_rate != second.mix_rate:
		error = "The recordings use different sample rates."
		return false
	var seconds_a := float(first.data.size() / 2) / first.mix_rate
	var seconds_b := float(second.data.size() / 2) / second.mix_rate
	segments_a = (metadata.get("segments_a", []) as Array).duplicate(true)
	segments_b = (metadata.get("segments_b", []) as Array).duplicate(true)
	if segments_a.is_empty():
		segments_a = [{"label": str(metadata.get("label_a", "A")), "start": 0.0, "end": seconds_a}]
	if segments_b.is_empty():
		segments_b = [{"label": str(metadata.get("label_b", "B")), "start": 0.0, "end": seconds_b}]
	if not _valid_segments(segments_a, float(metadata.get("seconds_a", seconds_a))) \
			or not _valid_segments(segments_b, float(metadata.get("seconds_b", seconds_b))):
		_clear()
		error = "The segment notes do not fit the recordings."
		return false
	pcm_a = first.data.duplicate()
	pcm_b = second.data.duplicate()
	rate = first.mix_rate
	samples_a = _decode(pcm_a)
	samples_b = _decode(pcm_b)
	peaks_a = _peaks(samples_a)
	peaks_b = _peaks(samples_b)
	label_a = str(metadata.get("label_a", "A")).to_upper()
	label_b = str(metadata.get("label_b", "B")).to_upper()
	alignment_required = bool(metadata.get("alignment_required", true))
	if metadata.has("expected_offset"):
		expected_offset = float(metadata.expected_offset)
	else:
		var anchor_a := _segment(segments_a, str(metadata.get("anchor_a", "")))
		var anchor_b := _segment(segments_b, str(metadata.get("anchor_b", "")))
		expected_offset = float(anchor_a.start) - float(anchor_b.start) \
			if not anchor_a.is_empty() and not anchor_b.is_empty() else 0.0
	timeline_start = floorf((minf(0.0, expected_offset) - 0.25) * 4.0) / 4.0
	timeline_end = ceilf((maxf(
		float(samples_a.size()) / rate,
		float(samples_b.size()) / rate + maxf(0.0, expected_offset)
	) + 0.25) * 4.0) / 4.0
	return true

func _clear() -> void:
	error = ""
	pcm_a.clear()
	pcm_b.clear()
	samples_a.clear()
	samples_b.clear()
	peaks_a.clear()
	peaks_b.clear()
	segments_a.clear()
	segments_b.clear()
	alignment_required = true
	label_a = "SATURDAY"
	label_b = "SUNDAY"
	timeline_start = -0.8
	timeline_end = 10.25

func _valid_stream(stream: AudioStreamWAV) -> bool:
	return stream != null and stream.format == AudioStreamWAV.FORMAT_16_BITS \
		and not stream.stereo and not stream.data.is_empty() \
		and stream.data.size() % 2 == 0 and stream.mix_rate > 0

func _valid_segments(segments: Array, seconds: float) -> bool:
	if segments.is_empty() or seconds <= 0.0:
		return false
	for item: Variant in segments:
		if not item is Dictionary:
			return false
		var entry := item as Dictionary
		var start := float(entry.get("start", -1.0))
		var end := float(entry.get("end", -1.0))
		if start < 0.0 or end <= start or end > seconds + 0.001:
			return false
	return true

func _segment(segments: Array, label: String) -> Dictionary:
	for item: Dictionary in segments:
		if str(item.get("label", "")) == label:
			return item
	return {}

func _decode(pcm: PackedByteArray) -> PackedFloat32Array:
	var decoded := PackedFloat32Array()
	decoded.resize(pcm.size() / 2)
	for index: int in decoded.size():
		decoded[index] = float(pcm.decode_s16(index * 2)) / 32768.0
	return decoded

func _peaks(samples: PackedFloat32Array) -> PackedVector2Array:
	var result := PackedVector2Array()
	var low := 0.0
	var high := 0.0
	for index: int in samples.size():
		var value := samples[index]
		low = minf(low, value)
		high = maxf(high, value)
		if (index + 1) % BIN_FRAMES == 0 or index == samples.size() - 1:
			result.append(Vector2(low, high))
			low = 0.0
			high = 0.0
	return result

func aligned(offset: float) -> bool:
	# One centisecond of adjustment tolerance avoids a pixel-perfect input gate.
	return not alignment_required or (is_finite(offset) and absf(offset - expected_offset) <= 0.015)

## Inside the accepted tolerance the tapes click into exact alignment, so identical parts
## play and draw as one voice instead of two copies a centisecond apart. Unscored
## comparisons never snap, so the second take follows the slider.
func effective_offset(offset: float) -> float:
	return expected_offset if alignment_required and aligned(offset) else offset

func playback(mode: String, offset: float) -> AudioStreamWAV:
	if samples_a.is_empty() or samples_b.is_empty() \
			or mode not in ["a", "b", "both"] or not is_finite(offset):
		return null
	var count := int(ceil((timeline_end - timeline_start) * rate))
	var out := PackedByteArray()
	out.resize(count * 2)
	var start_a := roundi(-timeline_start * rate)
	var start_b := roundi((clampf(effective_offset(offset), -0.75, 0.75) - timeline_start) * rate)
	for index: int in count:
		var a_index := index - start_a
		var b_index := index - start_b
		var value := 0
		if mode != "b" and a_index >= 0 and a_index < samples_a.size():
			value += pcm_a.decode_s16(a_index * 2)
		if mode != "a" and b_index >= 0 and b_index < samples_b.size():
			value += pcm_b.decode_s16(b_index * 2)
		if mode == "both":
			value = roundi(value * 0.5)
		out.encode_s16(index * 2, clampi(value, -32768, 32767))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.stereo = false
	stream.data = out
	return stream
