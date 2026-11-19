shader_type canvas_item;

uniform vec2 first_eye;
uniform vec2 second_eye;
uniform vec2 eye_radius;
uniform vec2 eye_travel;
varying vec4 tint;

void vertex() {
	tint = COLOR;
}

float pupil_region(vec2 uv, vec2 centre) {
	vec2 local = (uv - centre) / eye_radius;
	return 1.0 - smoothstep(0.52, 1.0, length(local));
}

void fragment() {
	float weight = max(pupil_region(UV, first_eye), pupil_region(UV, second_eye));
	COLOR = tint * texture(TEXTURE, UV - eye_travel * weight);
}
