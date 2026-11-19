shader_type canvas_item;

// A soft margin keeps the crop optically continuous with the background as the
// player moves the camera, while the object itself stays on the near focal plane.
uniform vec4 region = vec4(0.0,0.0,1.0,1.0);
void fragment() {
	vec2 local=(UV-region.xy)/region.zw;
	vec2 edge=smoothstep(vec2(0.0),vec2(0.20),local)*smoothstep(vec2(0.0),vec2(0.20),1.0-local);
	COLOR=texture(TEXTURE,UV)*vec4(1.0,1.0,1.0,edge.x*edge.y);
}
