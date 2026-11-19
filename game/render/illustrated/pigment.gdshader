shader_type canvas_item;
uniform float lantern : hint_range(0.0, 1.0) = 0.0;
void fragment() {
    vec4 ink = texture(TEXTURE, UV);
    // Preserve the painted facial features and introduce the warmth of the equipment lamp.
    ink.rgb *= vec3(0.93, 0.835, 0.82);
    ink.rgb += ink.rgb * vec3(0.075, 0.028, 0.006) * lantern;
    COLOR = ink;
}
