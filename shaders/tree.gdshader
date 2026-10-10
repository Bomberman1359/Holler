shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_draw_opaque;

#include "res://shaders/night.gdshaderinc"

uniform sampler2DArray tree_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray tree_nrh : filter_linear_mipmap, repeat_enable;
uniform float fade_from = 0.0;
uniform float fade_to = 0.0;
uniform float brightness = 1.0;

varying vec3 wpos;
varying vec3 wn;
varying vec3 wt;
varying vec3 wb;
varying float layer;
varying float shade;
varying float fade;
varying vec4 fog;

void vertex() {
	float phase = INSTANCE_CUSTOM.y;
	vec3 eye = CAMERA_POSITION_WORLD;
	fade = smoothstep(fade_from, fade_to, distance(MODEL_MATRIX[3].xz, eye.xz));
	if (fade >= 1.0) {
		VERTEX = vec3(0.0);
		wpos = MODEL_MATRIX[3].xyz;
		wn = vec3(0.0, 1.0, 0.0);
		wt = vec3(1.0, 0.0, 0.0);
		wb = vec3(0.0, 0.0, 1.0);
		layer = 0.0;
		shade = 0.0;
		fog = vec4(0.0);
	} else {
		shade = COLOR.r * brightness;
		layer = floor(COLOR.a * 2.0 + 0.5);
		float t = TIME * 0.6 + phase * 6.283;
		float sway = (sin(t) + 0.5 * sin(t * 2.3 + 1.7)) * 0.0035 * VERTEX.y;
		float tip = UV2.y * 0.006 * sin(TIME * 1.7 + phase * 40.0 + VERTEX.y * 30.0);
		VERTEX.x += sway + tip;
		VERTEX.z += sway * 0.6;
		VERTEX.y += tip * 0.5;
		wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
		wt = normalize((MODEL_MATRIX * vec4(TANGENT, 0.0)).xyz);
		wb = normalize((MODEL_MATRIX * vec4(BINORMAL, 0.0)).xyz);
		fog = mist(eye, wpos);
	}
}

void fragment() {
	if (fade > 0.0) {
		float n = fade_pattern(FRAGCOORD.xy);
		if (n < fade) {
			discard;
		}
	}
	vec4 a = texture(tree_albedo, vec3(UV, layer));
	vec3 n = wn;
	float wrap = 0.7;
	vec3 albedo = a.rgb * shade;
	if (layer > 0.5) {
		if (a.a < 0.5) {
			discard;
		}
		if (!FRONT_FACING) {
			n = -n;
		}
	} else {
		vec4 nrh = texture(tree_nrh, vec3(UV, 0.0));
		vec2 dn = vec2(nrh.a, nrh.g) * 2.0 - 1.0;
		n = normalize(wn + (wt * dn.x + wb * dn.y) * 1.3);
		wrap = 0.0;
		albedo *= 0.7 + 0.3 * smoothstep(0.0, 0.08, UV.y / 20.0);
	}
	vec3 lit = albedo * night_light(wpos, n, wrap, 1.0);
	ALBEDO = mix(lit, fog.rgb, fog.a);
}
