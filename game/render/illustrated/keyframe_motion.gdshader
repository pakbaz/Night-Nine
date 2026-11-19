shader_type canvas_item;
render_mode unshaded;

uniform sampler2D first_image : source_color, filter_linear, repeat_disable;
uniform sampler2D motion_vectors : filter_linear, repeat_disable;
uniform float progress : hint_range(0.0, 1.0) = 0.0;

vec3 vector_at(vec2 position, float side) {
    vec2 recorded_size = vec2(textureSize(motion_vectors, 0));
    vec2 local_uv = clamp(position, vec2(1.0 / recorded_size.x, 0.5 / recorded_size.y),
        vec2(1.0 - 1.0 / recorded_size.x, 1.0 - 0.5 / recorded_size.y));
    vec3 sample_value = texture(motion_vectors, vec2((local_uv.x + side) * 0.5, local_uv.y)).rgb;
    return vec3((sample_value.rg * 255.0 - 128.0) * (0.12 / 127.0), sample_value.b);
}

void fragment() {
    // Backtrace each point to the two original paintings. Two local estimates
    // follow a moving silhouette more closely than a single full-frame offset.
    vec3 forward = vector_at(UV, 0.0);
    vec3 backward = vector_at(UV, 1.0);
    forward = vector_at(UV - progress * forward.xy, 0.0);
    backward = vector_at(UV - (1.0 - progress) * backward.xy, 1.0);
    vec2 uv_a = UV - progress * forward.xy;
    vec2 uv_b = UV - (1.0 - progress) * backward.xy;
    float a = (1.0 - progress) * mix(0.35, 1.0, forward.z);
    float b = progress * mix(0.35, 1.0, backward.z);
    COLOR = mix(texture(first_image, uv_a), texture(TEXTURE, uv_b), b / max(a + b, 0.001));
}
