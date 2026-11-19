shader_type canvas_item;
uniform float progress : hint_range(0.0,1.0);
uniform int scene_kind = 0;
uniform vec2 beacon = vec2(.58,.255);
float hash(float n) { return fract(sin(n*127.68+61.9)*4537.21); }
void fragment() {
	float t=progress;
	float start=smoothstep(0.0,.12,t);
	float ink=0.0;
	vec3 tint=vec3(1.0,.67,.34);
	if (scene_kind==0) {
		for (int i=0; i<21; i++) {
			float k=float(i); float phase=clamp((t-.23*hash(k+5.0))/.9,0.0,1.0);
			vec2 pos=vec2(.24+.68*hash(k+3.0)-.023*phase,.58-.22*hash(k+31.0)-phase*(.13+.22*hash(k+48.0)));
			vec2 d=(UV-pos)*vec2(130.0,78.0);
			ink+=exp(-dot(d,d)*2.7) * (.40+.41*sin(phase*2.7)) + .14*exp(-dot(d,d)*.23);
		}
	} else if (scene_kind==1) {
		// A narrow signal leaves the antenna and briefly lights the sea mist.
		float launch = smoothstep(.08,.78,t);
		vec2 center = beacon + vec2(.006*launch, -.16*launch);
		vec2 d = (UV-center)*vec2(1.7778,1.0);
		float radius = length(d);
		float core = exp(-radius*radius/.000014);
		float halo = exp(-radius*radius/.00053);
		float wake = exp(-abs(d.x)*1650.0) * smoothstep(0.0,.012,d.y)
			* (1.0-smoothstep(.012,.11,d.y)) * step(UV.y,beacon.y);
		float lamp = exp(-length((UV-beacon)*vec2(1.7778,1.0))*190.0);
		ink = (.84*core + .32*halo + .17*wake)*sin(3.14159*clamp(t/.96,0.0,1.0))
			+ .30*lamp*(1.0-launch);
		tint=vec3(1.0,.83,.55);
	}
	float fading=smoothstep(.73,1.0,t);
	float coverage=clamp(ink*start,0.0,.94);
	COLOR=vec4(tint*coverage*(1.0-fading)/max(.0001,coverage+(1.0-coverage)*fading),coverage+(1.0-coverage)*fading);
}
