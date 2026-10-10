shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_draw_opaque;

#include "res://shaders/night.gdshaderinc"

uniform sampler2D height_map : filter_nearest, repeat_disable;
uniform sampler2D cover_map : filter_linear, repeat_disable;
uniform float map_size = 2816.0;
uniform float cell = 2.0;
uniform float spacing = 1.4;
uniform float reach = 34.0;
uniform int channel = 0;
uniform float size_min = 0.7;
uniform float size_max = 1.3;
uniform float sway = 1.0;
uniform float sink = 0.04;
uniform float brightness = 1.0;

varying vec3 wpos;
varying vec3 wn;
varying vec3 tint;
varying vec4 fog;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float height_at(vec2 xz) {
	vec2 f = (xz + map_size * 0.5) / cell;
	ivec2 i = ivec2(floor(f));
	vec2 t = fract(f);
	ivec2 top = textureSize(height_map, 0) - ivec2(2);
	i = clamp(i, ivec2(0), top);
	float a = texelFetch(height_map, i, 0).r;
	float b = texelFetch(height_map, i + ivec2(1, 0), 0).r;
	float c = texelFetch(height_map, i + ivec2(0, 1), 0).r;
	float d = texelFetch(height_map, i + ivec2(1, 1), 0).r;
	return mix(mix(a, b, t.x), mix(c, d, t.x), t.y);
}

void vertex() {
	vec3 slot = MODEL_MATRIX[3].xyz;
	vec2 key = floor(slot.xz / spacing + 0.5);
	float h1 = hash(key);
	float h2 = hash(key + vec2(17.3, 5.1));
	float h3 = hash(key + vec2(41.7, 93.2));
	float h4 = hash(key + vec2(7.1, 61.9));
	vec2 at = (key + vec2(h1, h2) * 0.9 - 0.45) * spacing;
	vec2 muv = (at + map_size * 0.5 + cell * 0.5) / (map_size + cell);
	vec4 dens = textureLod(cover_map, muv, 0.0);
	float want = channel == 0 ? dens.r : (channel == 1 ? dens.g : dens.b);
	float d = distance(at, CAMERA_POSITION_WORLD.xz);
	float grow = (1.0 - smoothstep(reach * 0.72, reach, d)) * step(h3, want);
	if (grow <= 0.001) {
		VERTEX = vec3(0.0);
		wpos = vec3(0.0);
		wn = vec3(0.0, 1.0, 0.0);
		tint = vec3(0.0);
		fog = vec4(0.0);
	} else {
		float s = mix(size_min, size_max, h4) * (0.35 + 0.65 * grow);
		float yaw = h1 * 6.2831 + h2 * 3.0;
		float c = cos(yaw);
		float sn = sin(yaw);
		vec3 v = VERTEX * s;
		float bend = sway * v.y * (sin(TIME * 1.3 + h1 * 30.0) * 0.06 + sin(TIME * 2.7 + h2 * 20.0) * 0.025);
		v.x += bend;
		v.z += bend * 0.6;
		vec3 r = vec3(v.x * c - v.z * sn, v.y, v.x * sn + v.z * c);
		vec3 ground = vec3(at.x, height_at(at) - sink * s, at.y);
		wpos = ground + r;
		VERTEX = wpos - slot;
		vec3 n = NORMAL;
		wn = normalize(vec3(n.x * c - n.z * sn, n.y, n.x * sn + n.z * c));
		tint = COLOR.rgb * brightness * (0.8 + 0.4 * h2);
		fog = mist(CAMERA_POSITION_WORLD, wpos);
	}
}

void fragment() {
	vec3 n = FRONT_FACING ? wn : -wn;
	vec3 lit = tint * night_light(wpos, n, 0.6, 1.0);
	ALBEDO = mix(lit, fog.rgb, fog.a);
}
