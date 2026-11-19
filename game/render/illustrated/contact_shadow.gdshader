shader_type canvas_item;
render_mode unshaded;

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float spread = max(0.0, 1.0 - dot(p, p));
	vec2 contact = (p - vec2(0.04, -0.12)) * vec2(1.7, 2.1);
	float core = max(0.0, 1.0 - dot(contact, contact));
	COLOR = vec4(0.10, 0.066, 0.045, 0.26 * spread * spread + 0.19 * core * core);
}
