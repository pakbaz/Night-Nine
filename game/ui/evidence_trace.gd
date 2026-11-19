extends Control
## Display the audible PCM on a common time axis for the two evidence strips.
const BIN_COUNT := 160
var envelope := PackedFloat32Array()

func configure(recording: AudioStreamWAV, seconds: float) -> void:
	custom_minimum_size = Vector2(230, 34)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	envelope.clear()
	if recording == null or seconds <= 0 or recording.format != AudioStreamWAV.FORMAT_16_BITS:
		return
	var pcm := recording.data
	var channels := 2 if recording.stereo else 1
	var frames := pcm.size() / (2 * channels)
	var axis_frames := maxi(frames, roundi(seconds * recording.mix_rate))
	envelope.resize(BIN_COUNT)
	for bin_index: int in BIN_COUNT:
		var first := floori(float(bin_index) * axis_frames / BIN_COUNT)
		var last := mini(frames, ceili(float(bin_index + 1) * axis_frames / BIN_COUNT))
		var peak := 0.0
		for frame: int in range(first, last, 4):
			peak = maxf(peak, absf(float(pcm.decode_s16(frame * channels * 2)) / 32768.0))
		envelope[bin_index] = peak
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color("102226"))
	var center := size.y * .5
	draw_line(Vector2(0, center), Vector2(size.x, center), Color("53605d"), 1)
	for i: int in envelope.size():
		var x := (i + .5) * size.x / BIN_COUNT
		var half_height := sqrt(envelope[i]) * (center - 2)
		if half_height > 0.1:
			draw_line(Vector2(x, center - half_height), Vector2(x, center + half_height), Color("e9c38b"), maxf(1, size.x / BIN_COUNT - .3))
