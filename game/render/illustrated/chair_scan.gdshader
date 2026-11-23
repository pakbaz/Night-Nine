shader_type canvas_item;
render_mode unshaded, blend_add;

uniform float phase = 0.0;

void fragment() {
	// The emitter is fixed in the painted hood. Follow Steve's reclined body,
	// widening the pool of light from his head to his knees and boots.
	float depth = clamp((UV.y - 0.28) / 0.47, 0.0, 1.0);
	float axis = mix(0.815, 0.893, smoothstep(0.0, 0.28, depth))
		- 0.155 * smoothstep(0.34, 1.0, depth);
	float side = (UV.x - axis) / mix(0.018, 0.070, depth);
	float cone = exp(-side * side * 1.8) * smoothstep(0.27, 0.32, UV.y)
		* (1.0 - smoothstep(0.73, 0.77, UV.y));
	float travel = 0.5 - 0.5 * cos(phase * TAU);
	float stripe = (UV.y - mix(0.39, 0.73, travel) + 0.006 * side * side) / 0.011;
	float lamp = length((UV - vec2(0.815, 0.281)) / vec2(0.030, 0.013));
	float intensity = cone * (0.10 + 0.75 * exp(-stripe * stripe))
		+ 0.4 * exp(-lamp * lamp);
	COLOR = vec4(0.47, 0.90, 1.0, intensity);
}
