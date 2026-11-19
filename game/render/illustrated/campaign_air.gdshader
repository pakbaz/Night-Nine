shader_type canvas_item;

// Near-camera rain, suspended dust or sea mist. The stage owns the clock so pausing
// in the middle of a spoken line holds these particles and the camera together.
uniform int medium = 0;
uniform float seconds = 0.0;
uniform vec4 light_color : source_color = vec4(0.8,0.7,0.5,1.0);
uniform vec2 source = vec2(0.75,0.32);
uniform vec4 window = vec4(-0.06,-0.06,1.12,1.12);

float random_cell(vec2 cell) {
	return fract(sin(dot(cell,vec2(127.1,311.7))) * 43758.5453);
}
void fragment() {
	vec2 uv=UV;
	float t=seconds;
	float alpha=0.0;
	float light=exp(-length((uv-source)*vec2(1.8,1.0))*3.8);
	if (medium==1) {
		vec2 lines=vec2(uv.x*1.78+uv.y*0.09,uv.y) * vec2(85.0,10.0);
		lines.y-=t*5.2;
		float seed=random_cell(floor(lines));
		vec2 local=fract(lines);
		float thread=1.0-smoothstep(0.018,0.068,abs(local.x-seed));
		alpha=thread*smoothstep(0.08,0.48,local.y)*(1.0-smoothstep(0.54,0.92,local.y))*step(0.84,seed)*0.21;
	} else if (medium==2) {
		float mist=sin(uv.x*16.0+t*0.21+sin(uv.y*8.0))*0.5+0.5;
		alpha=mist*exp(-pow((uv.y-0.57)*6.6,2.0))*0.045+light*0.026;
	} else {
		vec2 field=uv*vec2(23.0,16.0)+vec2(t*0.037,-t*0.064);
		vec2 cell=floor(field);
		float seed=random_cell(cell);
		vec2 center=vec2(seed,random_cell(cell+vec2(9.0,1.0)));
		vec2 offset=(fract(field)-center)*vec2(1.1,1.4);
		float dust=1.0-smoothstep(0.006,0.031,length(offset));
		alpha=dust*step(0.73,seed)*(0.14+light*0.44);
		if (medium==3) {
			alpha+=light*(0.030+0.017*sin(t*1.05));
		}
	}
	vec2 inside=smoothstep(window.xy,window.xy+0.032,uv)*(1.0-smoothstep(window.xy+window.zw-0.032,window.xy+window.zw,uv));
	COLOR=vec4(light_color.rgb,alpha*inside.x*inside.y);
}
