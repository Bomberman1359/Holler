shader_type spatial;
render_mode unshaded, fog_disabled, blend_mix, depth_draw_never, cull_disabled;

#include "res://shaders/night.gdshaderinc"

uniform float age = 0.0;
uniform float life = 18.0;

varying float fade;
varying float seed;
varying vec4 fog;
varying vec3 light;

void vertex() {
	float t = max(age - INSTANCE_CUSTOM.x, 0.0);
	float k = clamp(t / life, 0.0, 1.0);
	seed = INSTANCE_CUSTOM.w;
	vec3 center = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	center.y += INSTANCE_CUSTOM.y * (1.0 - exp(-t * 0.35)) * 3.0;
	center.xz += normalize(center.xz - NODE_POSITION_WORLD.xz + vec2(0.001)) * (1.0 - exp(-t * 0.25)) * INSTANCE_CUSTOM.y * 1.2;
	float size = INSTANCE_CUSTOM.z * (0.35 + 0.65 * (1.0 - exp(-t * 0.5))) * (1.0 + k);
	fade = smoothstep(0.0, 0.6, t) * (1.0 - k) * (1.0 - k) * step(INSTANCE_CUSTOM.x, age);
	vec3 right = INV_VIEW_MATRIX[0].xyz;
	vec3 up = INV_VIEW_MATRIX[1].xyz;
	vec3 at = center + (right * VERTEX.x + up * VERTEX.y) * size;
	fog = mist(CAMERA_POSITION_WORLD, at);
	light = night_light(center, vec3(0.0, 1.0, 0.0), 1.0, 1.0);
	POSITION = PROJECTION_MATRIX * (VIEW_MATRIX * vec4(at, 1.0));
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	float ragged = 0.5 + 0.5 * sin(atan(p.y, p.x) * 5.0 + seed * 40.0) * sin(atan(p.y, p.x) * 3.0 + seed * 17.0);
	float a = smoothstep(1.0, 0.25 + 0.25 * ragged, r);
	vec3 c = vec3(0.34, 0.33, 0.31) * (light * 1.6 + 0.05);
	ALBEDO = mix(c, fog.rgb, fog.a);
	ALPHA = a * fade * 0.6 * (1.0 - fog.a * 0.7);
}
