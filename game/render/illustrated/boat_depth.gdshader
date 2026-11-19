shader_type canvas_item;
// Keep the receiver, rope and seat in front of the seated pair.
// The gunwale and painted ribs sit on a lower layer using the same UV transform.
uniform float dial : hint_range(0.0,1.0)=0.0;
float inside_edge(vec2 p, vec2 a, vec2 b) {
	return (b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x);
}
float handle(vec2 p,vec2 a,vec2 b,float radius) {
	vec2 edge=b-a;
	float along=clamp(dot(p-a,edge)/dot(edge,edge),0.0,1.0);
	return 1.0-smoothstep(radius,radius+0.6,length(p-a-edge*along));
}
void fragment() {
	vec4 paint=texture(TEXTURE,UV);
	// Polygon around the radio case and its carrying handle.
	vec2 p=UV*vec2(711.0,400.0);
	float radio = step(0.0,min(min(inside_edge(p,vec2(123,223),vec2(147,211)),inside_edge(p,vec2(147,211),vec2(283,204))),
		min(min(inside_edge(p,vec2(283,204),vec2(313,219)),inside_edge(p,vec2(313,219),vec2(315,317))),
		min(inside_edge(p,vec2(315,317),vec2(125,327)),inside_edge(p,vec2(125,327),vec2(123,223))))));
	radio = max(radio, handle(p,vec2(160,205),vec2(280,197),3.4));
	radio = max(radio, handle(p,vec2(164,205),vec2(164,214),2.2));
	radio = max(radio, handle(p,vec2(273,198),vec2(273,207),2.5));
	float shelf = smoothstep(289.0,292.0,p.y);
	float notebook = step(0.0,min(min(inside_edge(p,vec2(404,294),vec2(463,272)),inside_edge(p,vec2(463,272),vec2(596,298))),
		min(inside_edge(p,vec2(596,298),vec2(564,342)),inside_edge(p,vec2(564,342),vec2(404,294)))));
	float rope = (1.0-smoothstep(86.0,120.0,p.x))*smoothstep(277.0,289.0,p.y);
	paint.a *= max(max(radio,shelf),max(notebook,rope));
	vec2 mark=(UV-vec2(.254+.077*dial,.615))/vec2(.002,.008);
	paint.rgb+=vec3(.8,.38,.08)*exp(-dot(mark,mark));
	COLOR=paint;
}
