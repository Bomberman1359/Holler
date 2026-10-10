shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

#include "res://shaders/night.gdshaderinc"

uniform sampler2D ripple : repeat_enable, filter_linear_mipmap;
uniform float shake = 0.0;

varying vec3 wpos;
varying float pond;
varying vec4 fog;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	pond = UV2.x;
	fog = mist(CAMERA_POSITION_WORLD, wpos);
}

void fragment() {
	vec3 eye = CAMERA_POSITION_WORLD;
	vec2 p = wpos.xz;
	float flow = (1.0 - pond) * TIME;
	vec2 n1 = texture(ripple, p * 0.09 + vec2(TIME * 0.011, flow * 0.03)).rg - 0.5;
	vec2 n2 = texture(ripple, p * 0.31 - vec2(TIME * 0.023, -flow * 0.05)).gb - 0.5;
	float rough = 0.35 + pond * shake * 2.5;
	vec3 n = normalize(vec3((n1.x + n2.x * 0.6) * rough, 1.0, (n1.y + n2.y * 0.6) * rough));
	vec3 v = normalize(eye - wpos);
	float facing = max(dot(n, v), 0.0);
	float fres = (1.0 - facing) * (1.0 - facing);
	fres *= fres;
	vec3 sky = mist_tint(eye, reflect(-v, n));
	vec3 col = mix(vec3(0.004, 0.007, 0.008), sky, 0.18 + 0.82 * fres);
	col += night_gloss(wpos, n, eye, 0.1) * 1.4;
	ALBEDO = mix(col, fog.rgb, fog.a);
}
