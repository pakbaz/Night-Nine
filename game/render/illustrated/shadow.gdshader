shader_type canvas_item;
void fragment() {
    vec2 d=(UV-0.5)*2.0;
    float shade=exp(-dot(d,d)*3.4)*(1.0-smoothstep(0.63,1.0,length(d)));
    COLOR=vec4(0.085,0.057,0.07,shade*0.65);
}
