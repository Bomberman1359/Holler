shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

#include "res://shaders/night.gdshaderinc"

uniform sampler2D height_map : filter_nearest, repeat_disable;
uniform sampler2D control_map : filter_linear, repeat_disable;
uniform sampler2D tint_map : filter_linear, repeat_disable;
uniform sampler2D normal_map : filter_linear, repeat_disable;
uniform sampler2DArray ground_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray ground_nrh : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float map_size = 2816.0;
uniform float cell = 2.0;
uniform float tile = 3.2;
uniform float far_sink = 0.0;
uniform float canopy = 0.0;
uniform float brightness = 1.0;
const float DETAIL_FROM = 30.0;
const float DETAIL_TO = 46.0;

varying vec3 wpos;
varying float lifted;
varying float fog_amount;

float height_at(vec2 xz) {
	ivec2 p = ivec2(round((xz + map_size * 0.5) / cell));
	p = clamp(p, ivec2(0), textureSize(height_map, 0) - ivec2(1));
	return texelFetch(height_map, p, 0).r;
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 off = UV2;
	float h;
	if (dot(off, off) > 0.01) {
		h = 0.5 * (height_at(w.xz + off) + height_at(w.xz - off));
	} else {
		h = height_at(w.xz);
	}
	lifted = 0.0;
	if (canopy > 0.0) {
		vec2 muv = (w.xz + map_size * 0.5 + cell * 0.5) / (map_size + cell);
		vec4 ctl = textureLod(control_map, muv, 0.0);
		lifted = ctl.r;
		h += canopy * ctl.r * (0.75 + 0.5 * fract(sin(dot(w.xz, vec2(12.9898, 78.233))) * 43758.5453));
	}
	if (far_sink > 0.0) {
		float d = distance(w.xz, CAMERA_POSITION_WORLD.xz);
		h -= far_sink * (1.0 - smoothstep(300.0, 460.0, d));
	}
	VERTEX.y = h;
	wpos = vec3(w.x, h, w.z);
	fog_amount = mist_amount(CAMERA_POSITION_WORLD, wpos);
}

void fragment() {
	vec3 eye = CAMERA_POSITION_WORLD;
	vec3 view = wpos - eye;
	float dist = length(view);
	vec3 tint = mist_tint(eye, view / dist);
	if (fog_amount > 0.985) {
		ALBEDO = tint;
	} else {
		vec2 muv = (wpos.xz + map_size * 0.5 + cell * 0.5) / (map_size + cell);
		vec4 ctl = texture(control_map, muv);
		vec4 tnt = texture(tint_map, muv);
		vec3 nm = texture(normal_map, muv).rgb;
		vec3 wn = vec3(nm.r * 2.0 - 1.0, 0.0, nm.g * 2.0 - 1.0);
		wn.y = sqrt(max(1.0 - wn.x * wn.x - wn.z * wn.z, 0.0));

		vec2 uv = wpos.xz / tile;
		vec2 dx = dFdx(uv);
		vec2 dy = dFdy(uv);
		float second = smoothstep(10.0, 22.0, dist) * 0.4;
		vec2 uv2 = wpos.zx / (tile * 3.7) + vec2(0.37, 0.11);
		float detail = 1.0 - smoothstep(DETAIL_FROM, DETAIL_TO, dist);
		vec3 albedo = vec3(0.0);
		vec4 nrh = vec4(0.0);
		float total = 0.0;
		for (int i = 0; i < 4; i++) {
			float wgt = ctl[i];
			if (wgt < 0.02) {
				continue;
			}
			float k = wgt * wgt;
			if (detail > 0.0) {
				vec4 n1 = textureGrad(ground_nrh, vec3(uv, float(i)), dx, dy);
				k *= mix(1.0, 0.35 + n1.b, detail);
				nrh += n1 * k;
			}
			vec3 a1 = textureGrad(ground_albedo, vec3(uv, float(i)), dx, dy).rgb;
			if (second > 0.0) {
				a1 = mix(a1, textureGrad(ground_albedo, vec3(uv2, float(i)), dx * 0.27, dy * 0.27).rgb, second);
			}
			albedo += a1 * k;
			total += k;
		}
		albedo /= max(total, 0.0001);
		float wet = tnt.a;
		albedo *= tnt.rgb * 2.0 * brightness;
		albedo *= mix(1.0, 0.55, wet);
		albedo *= clamp(0.55 + 0.9 * nm.b, 0.5, 1.15);
		if (canopy > 0.0) {
			albedo = mix(albedo, vec3(0.012, 0.02, 0.014), lifted);
		}

		vec3 n = wn;
		float rough = 0.9;
		if (detail > 0.0) {
			nrh /= max(total, 0.0001);
			vec2 dn = vec2(nrh.a, nrh.g) * 2.0 - 1.0;
			n = normalize(wn + vec3(dn.x, 0.0, -dn.y) * (0.9 * detail));
			rough = nrh.r;
		}
		vec3 lit = albedo * night_light(wpos, n, 0.45, 1.0);
		if (wet > 0.05) {
			lit += night_gloss(wpos, n, eye, mix(rough, 0.2, wet * 0.8)) * wet * 0.5;
		}
		ALBEDO = mix(lit, tint, fog_amount);
	}
}
