shader_type canvas_item;
render_mode unshaded;

uniform int shot : hint_range(1, 12) = 1;
uniform float progress : hint_range(0.0, 1.0) = 0.0;
uniform bool detail = true;
// When false the plate is never displaced: only light, the slow push and whole moving cut-outs.
uniform bool warp = false;
uniform sampler2D subject_tex : source_color, filter_linear, repeat_disable;
uniform float subject_aspect = 1.0;

varying vec4 paint_modulate;

void vertex() {
	paint_modulate = COLOR;
}

float pool(vec2 uv, vec2 center, vec2 radius) {
	vec2 delta = (uv - center) / radius;
	return exp(-dot(delta, delta));
}

float ripple(vec2 p, float t) {
	return sin(p.y * 151.0 + sin(p.x * 16.0 + t * 5.0) + t * 11.0)
		+ 0.43 * sin(p.y * 257.0 - p.x * 9.0 - t * 16.0);
}

// Transform only the metal hub and inner tyre. The painted mudguard stays on the body.
vec2 wheel_uv(vec2 uv, vec2 hub, float spin) {
	vec2 delta = (uv - hub) * vec2(subject_aspect, 1.0);
	float amount = 1.0 - smoothstep(0.065, 0.100, length(delta));
	float angle = -spin * amount;
	vec2 rotated = vec2(cos(angle) * delta.x - sin(angle) * delta.y,
		sin(angle) * delta.x + cos(angle) * delta.y);
	return hub + rotated / vec2(subject_aspect, 1.0);
}

vec4 painted_subject(vec2 point, vec2 center, vec2 size, float spin) {
	vec2 uv = (point - center) / size + vec2(0.5);
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) {
		return vec4(0.0);
	}
	if (shot == 6 && detail) {
		vec2 hub = vec2(uv.x < 0.50 ? 0.300 : 0.762, 0.897);
		uv = wheel_uv(uv, hub, spin);
	}
	return texture(subject_tex, uv);
}

vec3 moving_subject(vec3 paint, vec2 p, float t, float art_aspect) {
	float width;
	vec2 center;
	float waterline = 1.0;
	if (shot == 6) {
		width = 0.42;
		float road_y = 0.82 + 0.0012 * sin(t * 64.0);
		center = vec2(mix(-0.085, 1.092, t), road_y - width * art_aspect / subject_aspect * 0.50);
		paint *= 1.0 - 0.39 * pool(p, vec2(center.x, road_y - 0.004), vec2(width * 0.31, 0.010));
	} else if (shot == 9) {
		width = mix(0.82, 1.18, t);
		center = vec2(mix(1.03, 0.37, t), mix(0.26, 0.21, t));
		paint *= 1.0 - 0.13 * pool(p, vec2(center.x, 0.70), vec2(0.51, 0.25)) * smoothstep(0.02, 0.66, t);
	} else if (shot == 10) {
		width = mix(0.49, 0.56, t);
		waterline = 0.714;
		float hull_height = width * art_aspect / subject_aspect;
		center = vec2(mix(0.43, 0.54, t), waterline + hull_height * 0.29 - 0.56 * t);
	} else {
		// The festival plate already has a large stationary lantern at far right.
		// Float this boat through the open water between it and the timber pier.
		width = mix(0.153, 0.094, t);
		waterline = mix(0.835, 0.688, t) + 0.004 * sin(t * 13.0);
		center = vec2(mix(0.467, 0.735, t), waterline - width * art_aspect / subject_aspect * 0.387);
	}
	vec2 size = vec2(width, width * art_aspect / subject_aspect);
	float wave = ripple(p,t);
	if ((shot == 10 || shot == 11) && p.y > waterline) {
		float depth = p.y - waterline;
		vec2 reflected = vec2(p.x + (0.001 + depth * 0.045) * wave,
			waterline - depth * (shot == 10 ? 1.12 : 1.38));
		vec4 glint = painted_subject(reflected, center, size, 0.0);
		float breakup = (0.48 + 0.24 * wave) * exp(-depth * (shot == 10 ? 6.0 : 18.0));
		paint = mix(paint, glint.rgb * vec3(0.82, 0.84, 0.81), glint.a * breakup);
		if (shot == 11) {
			paint += vec3(0.23, 0.095, 0.018) * breakup * pool(p, vec2(center.x, waterline + 0.025), size * vec2(0.33, 0.56));
		}
	}
	vec4 layer = painted_subject(p, center, size, t * 47.0);
	if (shot == 10) {
		// The water hides the submerged hull and leaves a brief broken wake at the breach.
		float lip = waterline + 0.0020 * wave;
		layer.a *= 1.0 - smoothstep(lip - 0.002, lip + 0.003, p.y);
		float wake = sin(clamp(t / 0.73, 0.0, 1.0) * PI);
		float reach = mix(0.075, 0.36, t);
		float broken = 0.56 + 0.27 * sin(137.0 * p.x + t * 17.0) + 0.17 * sin(253.0 * p.x - t * 12.0);
		paint += vec3(0.24, 0.27, 0.24) * broken * wake * pool(p, vec2(center.x, lip), vec2(reach, 0.006 + 0.008 * wake));
	}
	if (shot == 9) {
		layer.rgb = mix(layer.rgb * vec3(0.82,0.85,0.94), vec3(0.24,0.24,0.32), 0.12);
	}
	return mix(paint, layer.rgb, layer.a);
}

void fragment() {
	float t = clamp(progress, 0.0, 1.0);
	t = mix(t, t * t * (3.0 - 2.0 * t), 0.48);
	float art_aspect = TEXTURE_PIXEL_SIZE.y / TEXTURE_PIXEL_SIZE.x;
	// Reframe inside the painted bleed throughout the shot. All object anchors
	// stay in the same coordinates as their road, sea horizon or strip of glass.
	vec2 aim = vec2(0.50, 0.49);
	if (shot == 2) { aim = vec2(0.69, 0.42); }
	else if (shot == 3) { aim = vec2(0.57, 0.59); }
	else if (shot == 4 || shot == 5) { aim = vec2(0.28, 0.47); }
	else if (shot == 8) { aim = vec2(0.78, 0.40); }
	float scale = mix(1.018, 1.074, t);
	if (shot == 6 || shot == 9 || shot == 10 || shot == 11) { scale = mix(1.014, 1.038, t); }
	vec2 p = (UV - aim) / scale + aim;
	vec2 sample_uv = p;
	vec2 still_uv = p;
	float swell = 0.0;
	float signal = 0.0;
	if (shot == 1) {
		float water = smoothstep(0.54, 0.81, p.y);
		swell = sin(22.0 * p.y - 7.0 * t + sin(4.2 * p.x + t));
		sample_uv.y += water * (0.0084 * swell + 0.0027 * sin(p.x * 12.0 + t * 5.0));
		sample_uv.x += water * 0.0035 * sin(37.0 * p.y + t * 7.0);
	} else if (shot == 2) {
		signal = pool(p, vec2(0.67,0.43), vec2(0.24,0.23));
		sample_uv.x += signal * sin(p.y * 38.0 - t * 8.0) * 0.0031;
	} else if (shot == 3) {
		float ping = pool(vec2(t,0.0),vec2(0.32,0.0),vec2(0.070,1.0))
			+ pool(vec2(t,0.0),vec2(0.58,0.0),vec2(0.069,1.0));
		signal = ping;
		sample_uv += vec2(0.0060,-0.0021) * sin(t * 192.0) * ping * pool(p,vec2(0.56,0.67),vec2(0.145,0.245));
	} else if (shot == 8) {
		sample_uv.x += 0.0019 * sin(p.y * 32.0 + t * 6.0) * (1.0 - smoothstep(0.25,0.62,p.y));
	} else if (shot == 9 || shot == 10 || shot == 11) {
		float edge = shot == 9 ? 0.69 : (shot == 10 ? 0.59 : 0.52);
		float water = smoothstep(edge,edge+0.18,p.y);
		// Leave the festival pier and townspeople at the two edges of the dawn plate fixed.
		if (shot == 11) { water *= smoothstep(0.36,0.59,p.x); }
		if (shot == 10) { water *= smoothstep(0.15,0.25,p.x) * (1.0-smoothstep(0.78,0.92,p.x)); }
		sample_uv.x += water * ripple(p,t) * 0.0023;
	} else if (shot == 12) {
		float foreground = smoothstep(0.70,0.99,p.y);
		sample_uv.x += foreground * (0.0054 * sin(9.0 * p.x - t * 9.0) + 0.0027 * sin(31.0 * p.x - t * 13.0));
		sample_uv.y += foreground * 0.0020 * cos(12.0 * p.x - t * 9.0);
	}
	if (!warp) { sample_uv = still_uv; }
	vec4 src = texture(TEXTURE, clamp(sample_uv, vec2(0.001), vec2(0.999)));
	vec3 paint = src.rgb;
	if (shot == 1) {
		float foam = max(0.0, min(paint.g, paint.b) - paint.r * 1.12);
		paint += vec3(0.04,0.32,0.31) * foam * (0.6 + 0.4 * swell) * smoothstep(0.55,0.76,p.y);
	} else if (shot == 2) {
		float breath = 0.5 - 0.5 * cos(t * 10.0);
		paint *= 0.94 + 0.06 * breath;
		paint += vec3(0.17,0.085,0.018) * signal * breath * (0.35 + paint.r);
	} else if (shot == 3) {
		float screen_light = pool(p,vec2(0.591,0.604),vec2(0.074,0.12));
		paint += vec3(0.012,0.16,0.23) * signal * screen_light;
		if (detail) {
			float glass = smoothstep(0.30,0.48,p.x) * (1.0-smoothstep(0.33,0.42,p.y));
			float trails = pow(max(0.0,sin((p.x + p.y * 0.12) * 244.0)),20.0);
			float beads = pow(max(0.0,sin(p.y * 60.0 - t * 35.0 + 17.0 * sin(p.x * 209.0))),9.0);
			paint += vec3(0.105,0.14,0.18) * trails * beads * glass;
		}
	} else if (shot == 4) {
		float dx = p.x - 0.245;
		float axis = 0.291 + dx * mix(0.46,0.10,t);
		float lane = (p.y-axis) / (0.008 + 0.112 * max(dx,0.0));
		float beam = exp(-lane*lane) * smoothstep(0.0,0.06,dx) * (1.0-smoothstep(0.23,0.62,dx));
		paint += vec3(0.32,0.235,0.14) * beam * (0.67 + 0.33*sin(15.0*p.x - t*4.0));
	} else if (shot == 5) {
		float first = pool(p,vec2(0.158,0.533),vec2(0.105,0.12));
		float second = pool(p,vec2(0.365,0.558),vec2(0.067,0.10));
		float a = smoothstep(0.04,0.38,t);
		float b = smoothstep(0.44,0.85,t);
		paint *= 1.0 - 0.39 * (first * (1.0-a) + second * (1.0-b));
		paint += vec3(0.16,0.085,0.025) * (first*a + second*b);
	} else if (shot == 7) {
		float hatch = pool(p,vec2(0.35,0.57),vec2(0.205,0.34));
		float distance_to_shadow = (p.x + 0.19 * p.y - mix(0.10,0.83,t)) / 0.063;
		paint *= 1.0 - 0.41 * hatch * exp(-distance_to_shadow*distance_to_shadow);
	} else if (shot == 8) {
		float glass = (1.0-smoothstep(0.29,0.64,p.y)) * pool(p,vec2(0.53,0.18),vec2(0.51,0.41));
		float path = sin(37.0*p.x + 20.0*p.y + 2.0*sin(10.0*p.y+t*4.0) - t*5.0)
			+ sin(19.0*p.x - 39.0*p.y + 1.4*cos(12.0*p.x-t*3.0));
		float caustic = exp(-8.0*path*path) * (0.26 + 0.74*smoothstep(0.02,0.5,paint.g));
		paint += vec3(0.040,0.155,0.132) * glass * caustic;
	} else if (shot == 12) {
		float wind = (0.5+0.5*sin(10.0*p.x-t*7.0 + p.y*4.0));
		float glass = max(0.0,paint.r-paint.b) * (1.0-smoothstep(0.57,0.8,p.y));
		paint += vec3(0.14,0.085,0.022) * wind * glass;
	}
	if (shot == 6 || shot == 9 || shot == 10 || shot == 11) {
		paint = moving_subject(paint,p,t,art_aspect);
	}
	COLOR = vec4(paint,src.a) * paint_modulate;
}
