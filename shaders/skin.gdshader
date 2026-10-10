shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

#include "res://shaders/night.gdshaderinc"

uniform float bones[336];

uniform vec3 tint = vec3(1.0);
uniform float own_light = 0.0;
uniform float wet = 0.15;
uniform float rim = 0.35;
uniform float pattern = 1.0;
uniform float veins = 0.5;
uniform vec3 vein_color = vec3(0.34, 0.30, 0.42);
uniform float vein_stretch = 1.0;
uniform float scope_glow = 0.0;
uniform float eye_shine = 0.0;

varying vec3 wpos;
varying vec3 wn;
varying vec3 rest;
varying vec4 paint;
varying float shine;
varying vec4 fog;

float hash3(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

void vertex() {
	rest = vec3(UV, UV2.x);
	shine = UV2.y;
	paint = COLOR;
	vec3 p = vec3(0.0);
	vec3 n = vec3(0.0);
	for (int k = 0; k < 4; k++) {
		float w = CUSTOM1[k];
		if (w > 0.0) {
			int o = int(CUSTOM0[k] + 0.5) * 12;
			vec3 r0 = vec3(bones[o], bones[o + 1], bones[o + 2]);
			vec3 r1 = vec3(bones[o + 4], bones[o + 5], bones[o + 6]);
			vec3 r2 = vec3(bones[o + 8], bones[o + 9], bones[o + 10]);
			p += w * (vec3(dot(r0, VERTEX), dot(r1, VERTEX), dot(r2, VERTEX)) + vec3(bones[o + 3], bones[o + 7], bones[o + 11]));
			n += w * vec3(dot(r0, NORMAL), dot(r1, NORMAL), dot(r2, NORMAL));
		}
	}
	VERTEX = p;
	NORMAL = normalize(n);
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	fog = mist(CAMERA_POSITION_WORLD, wpos);
}

void fragment() {
	vec3 eye = CAMERA_POSITION_WORLD;
	vec3 n = normalize(wn);
	vec3 p = rest * pattern;
	float blotch = vnoise(p * 6.0) * 0.6 + vnoise(p * 17.0) * 0.4;
	float net = abs(vnoise(p * vec3(11.0, 5.0 * vein_stretch, 11.0) + 3.7) - 0.5);
	float vein = smoothstep(0.035, 0.0, net) * smoothstep(0.35, 0.7, vnoise(p * 2.3 + 9.1)) * veins;
	vec3 albedo = paint.rgb * tint * (0.74 + 0.5 * blotch);
	albedo = mix(albedo, albedo * vein_color * 1.6, vein);
	float open = mix(0.22, 1.0, paint.a);
	vec3 lit = albedo * (night_light(wpos, n, 0.3, 1.0) * open + own_light * (0.5 + 0.5 * open));
	lit += night_gloss(wpos, n, eye, 0.55 - 0.4 * shine) * (wet + shine) * open;
	vec3 v = normalize(eye - wpos);
	float edge = 1.0 - max(dot(n, v), 0.0);
	lit += albedo * (edge * edge * edge) * rim * (sky_light.rgb * 3.0 + moon_light.rgb);
	lit += vec3(0.5, 0.6, 0.5) * scope_glow * (0.3 + 0.7 * edge);
	float eyes = smoothstep(0.85, 1.0, shine);
	lit += vec3(0.9, 1.0, 0.85) * eyes * (eye_shine + scope_glow * 6.0);
	ALBEDO = mix(lit, fog.rgb, fog.a);
}
