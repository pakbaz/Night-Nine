shader_type canvas_item;
uniform float seconds;
uniform float shimmer : hint_range(0.0,1.0);
void fragment() {
	vec2 p=UV;
	float water=smoothstep(.47,.64,p.y)*(1.0-smoothstep(.89,1.0,p.y));
	float ripples=sin(p.y*101.0+seconds*1.52+sin(p.x*13.0));
	p.x+=water*ripples*.0008;
	vec4 paint=texture(TEXTURE,clamp(p,vec2(0),vec2(1)));
	vec2 delta=(UV-vec2(.68,.65))/vec2(.32,.12);
	float swell=water*exp(-dot(delta,delta))*shimmer;
	paint.rgb+=vec3(.025,.36,.30)*swell*(.84+.16*ripples);
	COLOR=paint;
}
