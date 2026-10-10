shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

#include "res://shaders/night.gdshaderinc"

uniform sampler2DArray structure_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray structure_nrh : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D blotch : repeat_enable, filter_linear_mipmap;
uniform float glow_gain = 1.0;
const float BUMP_FROM = 18.0;
const float BUMP_TO = 28.0;

varying vec3 wpos;
varying vec3 wn;
varying vec3 wt;
varying vec3 wb;
varying float layer;
varying float glow;
varying float low;
varying vec4 tint;
varying vec4 fog;

void vertex() {
	low = VERTEX.y;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	wt = normalize((MODEL_MATRIX * vec4(TANGENT, 0.0)).xyz);
	wb = normalize((MODEL_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	layer = floor(UV2.x + 0.5);
	glow = UV2.y;
	tint = COLOR;
	fog = mist(CAMERA_POSITION_WORLD, wpos);
}

void fragment() {
	vec3 eye = CAMERA_POSITION_WORLD;
	float dist = distance(wpos, eye);
	vec3 albedo = texture(structure_albedo, vec3(UV, layer)).rgb * tint.rgb * 2.0;
	float st = texture(blotch, wpos.xz * 0.043 + wpos.y * 0.061).b;
	albedo *= 0.72 + 0.56 * st;
	albedo *= mix(0.62, 1.0, smoothstep(-0.1, 1.2, low + st * 0.5));
	vec3 n = normalize(wn);
	float rough = 0.9;
	if (dist < BUMP_TO) {
		vec4 nrh = texture(structure_nrh, vec3(UV, layer));
		vec2 dn = (vec2(nrh.a, nrh.g) * 2.0 - 1.0) * (1.0 - smoothstep(BUMP_FROM, BUMP_TO, dist)) * 1.3;
		n = normalize(n + normalize(wt) * dn.x + normalize(wb) * dn.y);
		rough = nrh.r;
	}
	vec3 lit = albedo * night_light(wpos, n, 0.0, tint.a);
	if (rough < 0.7) {
		lit += night_gloss(wpos, n, eye, rough) * 0.5;
	}
	lit += tint.rgb * (glow * glow_gain * 4.0);
	ALBEDO = mix(lit, fog.rgb, fog.a);
}
