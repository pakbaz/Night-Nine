class_name NightTapeRecording
extends RefCounted
## Preserve one PCM master. Two captures differ only in recorder start time.
const BIN_FRAMES := 64
var pcm := PackedByteArray()
var samples := PackedFloat32Array()
var peaks := PackedVector2Array()
var rate := 24000
var lead_a := 0.2
var lead_b := 0.55
var timeline_start := -0.25
var timeline_end := 3.0
var error := ""

func configure(master: AudioStreamWAV, first_lead: float, second_lead: float) -> bool:
	error = ""
	pcm.clear()
	samples.clear()
	peaks.clear()
	if master == null or master.format != AudioStreamWAV.FORMAT_16_BITS or master.stereo or master.data.is_empty() or master.data.size() % 2 != 0 or master.mix_rate <= 0:
		error = "This comparison requires the original mono PCM recording."
		return false
	if not is_finite(first_lead) or not is_finite(second_lead) or first_lead < 0 or second_lead < 0:
		error = "The capture start times are unavailable."
		return false
	pcm = master.data.duplicate()
	rate = master.mix_rate
	lead_a = first_lead
	lead_b = second_lead
	samples.resize(pcm.size() / 2)
	peaks.clear()
	var low := 0.0
	var high := 0.0
	for i: int in samples.size():
		var value := float(pcm.decode_s16(i * 2)) / 32768.0
		samples[i] = value
		low = minf(low, value)
		high = maxf(high, value)
		if (i + 1) % BIN_FRAMES == 0 or i == samples.size() - 1:
			peaks.append(Vector2(low, high))
			low = 0
			high = 0
	timeline_end = ceilf((float(samples.size()) / rate + maxf(lead_a, lead_b) + 0.8) * 4.0) / 4.0
	return not samples.is_empty()

func aligned(offset: float) -> bool:
	# One centisecond of adjustment tolerance avoids a pixel-perfect input gate.
	return is_finite(offset) and absf(lead_b + offset - lead_a) <= 0.015

func playback(mode: String, offset: float) -> AudioStreamWAV:
	if samples.is_empty() or mode not in ["a", "b", "both"] or not is_finite(offset):
		return null
	var count := int(ceil((timeline_end - timeline_start) * rate))
	var out := PackedByteArray()
	out.resize(count * 2)
	var start_a := roundi((lead_a - timeline_start) * rate)
	var start_b := roundi((lead_b + clampf(offset, -0.75, 0.75) - timeline_start) * rate)
	for i: int in count:
		var a := i - start_a
		var b := i - start_b
		var value := 0
		if mode != "b" and a >= 0 and a < samples.size():
			value += pcm.decode_s16(a * 2)
		if mode != "a" and b >= 0 and b < samples.size():
			value += pcm.decode_s16(b * 2)
		if mode == "both":
			value = roundi(value * 0.5)
		out.encode_s16(i * 2, value)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.stereo = false
	stream.data = out
	return stream
