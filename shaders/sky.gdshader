shader_type spatial;
render_mode unshaded, fog_disabled, cull_front, shadows_disabled, world_vertex_coords;

#include "res://shaders/night.gdshaderinc"

uniform sampler2D cloud_noise : repeat_enable, filter_linear_mipmap;
uniform vec4 sky_zenith : source_color = vec4(0.006, 0.010, 0.022, 1.0);
uniform vec4 sky_horizon : source_color = vec4(0.020, 0.030, 0.052, 1.0);
uniform float cloud_cover = 0.45;
uniform float overcast = 0.0;
uniform vec4 overcast_color : source_color = vec4(0.5, 0.52, 0.55, 1.0);

varying vec3 dir;

float hash3(vec3 p) {
	return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

void vertex() {
	dir = normalize(VERTEX);
	VERTEX += CAMERA_POSITION_WORLD;
}

void fragment() {
	vec3 d = normalize(dir);
	vec3 moon = moon_dir;
	vec3 c = mix(sky_horizon.rgb, sky_zenith.rgb, smoothstep(0.0, 0.7, d.y));
	vec3 cellp = floor(d * 260.0);
	float star = step(0.9935, hash3(cellp));
	float bright = hash3(cellp + 7.0);
	float md = dot(d, moon);
	c += vec3(0.75, 0.80, 0.95) * star * bright * bright * 0.5 * smoothstep(0.02, 0.25, d.y) * (1.0 - smoothstep(0.9, 0.995, md));
	c += vec3(1.0, 0.97, 0.88) * smoothstep(0.99955, 0.99975, md) * 1.4;
	c += vec3(0.10, 0.125, 0.17) * pow(max(md, 0.0), 60.0);
	c += vec3(0.03, 0.04, 0.06) * pow(max(md, 0.0), 6.0);
	if (d.y > 0.01) {
		vec2 cuv = d.xz / (d.y + 0.25) * 0.35 + vec2(TIME * 0.0015, TIME * 0.0007);
		float n = texture(cloud_noise, cuv).r * 0.6 + texture(cloud_noise, cuv * 2.7 + 0.3).r * 0.4;
		float cl = smoothstep(1.0 - cloud_cover, 1.0 - cloud_cover + 0.35, n) * smoothstep(0.01, 0.2, d.y);
		vec3 cloud_col = vec3(0.022, 0.028, 0.042) + vec3(0.16, 0.18, 0.22) * pow(max(md, 0.0), 12.0);
		c = mix(c, cloud_col, cl * 0.85);
	}
	if (overcast > 0.0) {
		float n = texture(cloud_noise, d.xz / (abs(d.y) + 0.3) * 0.2).r;
		c = mix(c, overcast_color.rgb * (0.9 + 0.25 * n), overcast);
	}
	vec3 eye = CAMERA_POSITION_WORLD;
	vec4 m = mist(eye, eye + d * mist_far);
	ALBEDO = mix(c, m.rgb, m.a);
}
