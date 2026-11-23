shader_type canvas_item;
// Keep the receiver, rope and seat in front of the seated pair.
// The gunwale and painted ribs sit on a lower layer using the same UV transform.
uniform float dial : hint_range(0.0,1.0)=0.0;
// Needle geometry in the 711 x 400 foreground space: the cap's centre, the pointer's length,
// and its angle from vertical (degrees) at each end of the band.
const vec2 NEEDLE_PIVOT=vec2(233.0,261.4);
const float NEEDLE_LENGTH=34.0;
const float NEEDLE_LEFT=-58.0;
const float NEEDLE_RIGHT=40.0;
// The dial glass, as a rounded rectangle: the needle is behind it and never crosses the frame.
const vec2 GLASS_CENTRE=vec2(223.6,245.0);
const vec2 GLASS_HALF=vec2(45.5,17.4);
const float GLASS_CORNER=5.0;
float behind_glass(vec2 p) {
	vec2 q=abs(p-GLASS_CENTRE)-GLASS_HALF+vec2(GLASS_CORNER);
	float outside=length(max(q,0.0))+min(max(q.x,q.y),0.0)-GLASS_CORNER;
	return 1.0-smoothstep(-0.6,0.4,outside);
}
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
	// The tuning needle: one orange pointer pivoting at its brass cap and sweeping the green
	// scale from 810 kHz (left) to 820 kHz (right). The painting itself has no needle.
	float swing=radians(mix(NEEDLE_LEFT,NEEDLE_RIGHT,dial));
	vec2 toward=vec2(sin(swing),-cos(swing));
	vec2 rel=p-NEEDLE_PIVOT;
	float along=clamp(dot(rel,toward),0.0,NEEDLE_LENGTH);
	float off=length(rel-toward*along);
	float needle=(1.0-smoothstep(0.35,0.95,off))*step(0.0,dot(rel,toward))*behind_glass(p);
	float cap=1.0-smoothstep(2.3,3.1,length(rel*vec2(1.0,1.15)));
	vec3 brass=vec3(.86,.46,.10);
	paint.rgb=mix(paint.rgb,brass*(.82+.18*along/NEEDLE_LENGTH),needle);
	paint.rgb=mix(paint.rgb,brass*.92+vec3(.10,.07,.02)*smoothstep(1.4,0.0,length(rel+vec2(.6,.8))),cap);
	paint.a=max(paint.a,max(needle,cap));
	COLOR=paint;
}
