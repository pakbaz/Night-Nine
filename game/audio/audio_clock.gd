class_name NightAudioClock
## Where the listener is in a sound right now.

## The published web build reports the audible position directly (see tools/build-pages.py).
## Desktop builds report the last mixed block, so add the time since that mix and remove
## the output latency.
static func audible_position(player: AudioStreamPlayer) -> float:
	var at := player.get_playback_position()
	if OS.has_feature("web") or player.stream_paused or OS.has_feature("movie"):
		return at
	return at + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
