shader_type canvas_item;
void fragment() {
	float shade=0.64*(1.0-smoothstep(0.0,0.23,UV.y))+0.30*smoothstep(0.84,1.0,UV.y);
	COLOR=vec4(.012,.022,.035,shade);
}
