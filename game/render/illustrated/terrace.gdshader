shader_type canvas_item;
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
float noise(vec2 p) {
    vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(hash(i),hash(i+vec2(1.0,0.0)),f.x),mix(hash(i+vec2(0.0,1.0)),hash(i+1.0),f.x),f.y);
}
void fragment() {
    // Worn slate. The converging inlays belong to the balcony floor, below the city skyline.
    float depth=UV.y+0.13;
    vec2 ground=vec2((UV.x-0.56)/depth,1.0/depth);
    float strata=0.45*noise(ground*vec2(11.0,23.0))+0.32*noise(ground*vec2(31.0,38.0))+0.23*noise(ground*vec2(103.0,141.0));
    vec3 rock=mix(vec3(0.115,0.094,0.108),vec3(0.226,0.184,0.177),strata);
    float slab=(1.0-smoothstep(0.008,0.038,abs(fract(ground.y*1.05)-0.5)));
    float radial=(1.0-smoothstep(0.006,0.022,abs(fract(ground.x*2.8)-0.5)));
    rock*=1.0-max(slab,radial)*0.23;
    float edge=(1.0-smoothstep(0.003,0.021,UV.y))*0.75;
    rock=mix(rock,vec3(0.45,0.322,0.27),edge);
    COLOR=vec4(rock,1.0);
}
