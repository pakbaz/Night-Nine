shader_type canvas_item;
uniform float signal : hint_range(0.0, 1.0) = 0.0;
void fragment() {
    vec4 metal = texture(TEXTURE, UV);
    vec2 dial = (UV - vec2(0.749,0.775)) / vec2(0.025,0.045);
    float lamp = exp(-dot(dial,dial)*1.4);
    metal.rgb *= vec3(0.86,0.80,0.80);
    metal.rgb += vec3(0.27,0.095,0.012)*lamp*signal;
    COLOR = metal;
}
