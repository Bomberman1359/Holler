shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_draw_opaque, world_vertex_coords;

#include "res://shaders/night.gdshaderinc"

const int ROWS = 11;
uniform sampler2DArray tree_albedo : source_color, filter_linear_mipmap, repeat_disable;
uniform float band[44];
uniform vec4 half_width;
uniform float fade_from = 0.0;
uniform float fade_to = 0.0;
uniform float brightness = 1.0;

varying float fade;
varying float cut;
varying vec3 light;
varying vec4 fog;

void vertex() {
	int kind = int(INSTANCE_CUSTOM.x + 0.5);
	int row = int(UV2.x + 0.5);
	float side = UV.x;
	float up_share = UV2.y;
	vec3 foot = MODEL_MATRIX[3].xyz;
	vec3 up = MODEL_MATRIX[1].xyz;
	float tall = length(up);
	vec3 eye = CAMERA_POSITION_WORLD;
	vec2 to_eye = eye.xz - foot.xz;
	float dist = length(to_eye);
	vec3 right = vec3(to_eye.y, 0.0, -to_eye.x) / max(dist, 0.001);
	float w = band[kind * ROWS + row];
	float t = TIME * 0.6 + INSTANCE_CUSTOM.y * 6.283;
	float sway = (sin(t) + 0.5 * sin(t * 2.3 + 1.7)) * 0.0035 * up_share * tall;
	vec3 p = foot + up * up_share + right * (side * w * half_width[kind] * tall) + vec3(sway, 0.0, sway * 0.6);
	UV = vec2((float(kind) + 0.5 + side * 0.5 * w) * 0.25, (1.0 - up_share) * 0.99609 + 0.00195);
	fade = smoothstep(fade_from, fade_to, dist);
	fog = mist(eye, p);
	cut = mix(0.5, 0.4, clamp(dist / 90.0, 0.0, 1.0));
	vec3 n = normalize(vec3(to_eye.x, dist * 0.6, to_eye.y));
	light = COLOR.rgb * brightness * night_light(p, n, 0.7, 1.0);
	if (fade <= 0.0 || fog.a > 0.99) {
		p = foot;
	}
	VERTEX = p;
}

void fragment() {
	if (fade < 1.0) {
		float n = fade_pattern(FRAGCOORD.xy);
		if (n >= fade) {
			discard;
		}
	}
	vec4 a = texture(tree_albedo, vec3(UV, 2.0));
	if (a.a < cut) {
		discard;
	}
	ALBEDO = mix(a.rgb * light, fog.rgb, fog.a);
}
