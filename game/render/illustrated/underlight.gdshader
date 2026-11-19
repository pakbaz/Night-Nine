shader_type canvas_item;

uniform float progress : hint_range(0.0, 1.0);
void fragment() {
	vec2 uv = UV;
	// The lower-left triangular section is the wooden gunwale.
	float water = 1.0 - smoothstep(.448 + 1.08*uv.x, .49 + 1.08*uv.x, uv.y);
	float wave = sin(uv.y*51.0 + uv.x*13.0 + progress*3.8);
	vec2 drift = vec2(wave, .45*sin(uv.x*28.0-progress*2.8));
	vec3 paint = texture(TEXTURE, clamp(uv + drift*.00135*water, vec2(0.0), vec2(1.0))).rgb;
	float cyan = smoothstep(.025,.29, min(paint.g,paint.b)-paint.r);
	float exposure = mix(.66,1.30,smoothstep(.04,.74,progress));
	COLOR = vec4(paint*mix(1.0,exposure,cyan*water),1.0);
}
