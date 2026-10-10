global uniform vec4 mist_layer;
global uniform vec4 mist_color : source_color;
global uniform vec4 mist_up : source_color;
global uniform vec4 mist_top : source_color;
global uniform vec4 mist_glow : source_color;
global uniform float mist_far;

global uniform vec3 moon_dir;
global uniform vec4 moon_light;
global uniform vec4 sky_light;
global uniform vec4 ground_light;
global uniform vec4 lamp_cone;
global uniform vec3 lamp_at;
global uniform vec4 lamp_light;
global uniform vec4 lamp_shape;
global uniform vec4 glow0_at;
global uniform vec4 glow0_light;
global uniform vec4 glow1_at;
global uniform vec4 glow1_light;
global uniform vec4 glow2_at;
global uniform vec4 glow2_light;

float _mist_g(float y) {
	float w = mist_layer.w - mist_layer.z;
	float a = min(y, mist_layer.z) - mist_layer.z;
	float u = clamp(mist_layer.w - y, 0.0, w);
	return a + (w * w - u * u) / (2.0 * w);
}

float mist_amount(vec3 eye, vec3 at) {
	float t = distance(eye, at);
	float dy = at.y - eye.y;
	float mean;
	if (abs(dy) > 0.05) {
		mean = (_mist_g(at.y) - _mist_g(eye.y)) / dy;
	} else {
		mean = clamp((mist_layer.w - eye.y) / (mist_layer.w - mist_layer.z), 0.0, 1.0);
	}
	float tau = t * (mist_layer.y + (mist_layer.x - mist_layer.y) * mean);
	return 1.0 - exp(-tau);
}

vec3 mist_tint(vec3 eye, vec3 dir) {
	float above = smoothstep(mist_layer.z, mist_layer.w + 20.0, eye.y);
	vec3 inside = mix(mist_color.rgb, mist_up.rgb, smoothstep(-0.05, 0.75, dir.y));
	vec3 c = mix(inside, mix(mist_top.rgb, mist_up.rgb, smoothstep(-0.02, 0.3, dir.y)), above);
	float m = max(dot(dir, moon_dir), 0.0);
	float m2 = m * m;
	float m4 = m2 * m2;
	float m8 = m4 * m4;
	float m32 = m8 * m8 * m8 * m8;
	c += mist_glow.rgb * (m4 * m * 0.6 + m32 * m8);
	float beam = smoothstep(0.86, 0.985, dot(dir, lamp_cone.xyz));
	c += lamp_light.rgb * (lamp_cone.w * beam * 0.0062 * (1.0 - above));
	return c;
}

vec4 mist(vec3 eye, vec3 at) {
	vec3 dir = normalize(at - eye);
	return vec4(mist_tint(eye, dir), mist_amount(eye, at));
}

float lamp_reach(vec3 at, out vec3 dir) {
	vec3 to = at - lamp_at;
	float d2 = dot(to, to);
	float d = sqrt(d2);
	dir = to / max(d, 0.001);
	float c = dot(dir, lamp_cone.xyz);
	float cone = smoothstep(lamp_shape.x, lamp_shape.y, c);
	cone *= 0.55 + 0.45 * smoothstep(lamp_shape.y, 1.0, c);
	float edge = clamp(1.0 - d / lamp_light.a, 0.0, 1.0);
	float near = 1.15 * d / (d + 1.2);
	return lamp_cone.w * cone * edge * edge * near * exp(-lamp_shape.z * d) / (1.0 + d2 * 0.03);
}

float _facing(float ndl, float wrap) {
	return max((ndl + wrap) / (1.0 + wrap), 0.0);
}

vec3 _glow(vec4 where, vec4 light, vec3 at, vec3 n, float wrap) {
	vec3 to = where.xyz - at;
	float d2 = dot(to, to);
	if (d2 >= where.w * where.w) {
		return vec3(0.0);
	}
	float d = sqrt(d2);
	float edge = 1.0 - d / where.w;
	return light.rgb * (edge * edge / (1.0 + d2 * 0.06) * _facing(dot(n, to / max(d, 0.001)), wrap));
}

vec3 night_light(vec3 at, vec3 n, float wrap, float sky) {
	vec3 l = mix(ground_light.rgb, sky_light.rgb, n.y * 0.5 + 0.5);
	l += moon_light.rgb * _facing(dot(n, moon_dir), wrap);
	l *= sky;
	vec3 dir;
	float reach = lamp_reach(at, dir);
	l += lamp_light.rgb * (reach * _facing(-dot(n, dir), wrap));
	l += _glow(glow0_at, glow0_light, at, n, wrap);
	l += _glow(glow1_at, glow1_light, at, n, wrap);
	l += _glow(glow2_at, glow2_light, at, n, wrap);
	return l;
}

vec3 night_gloss(vec3 at, vec3 n, vec3 eye, float rough) {
	vec3 v = normalize(eye - at);
	float power = mix(140.0, 5.0, rough);
	float amount = (1.0 - rough) * (1.0 - rough);
	vec3 s = moon_light.rgb * (pow(max(dot(n, normalize(v + moon_dir)), 0.0), power) * 2.5);
	vec3 dir;
	float reach = lamp_reach(at, dir);
	s += lamp_light.rgb * (reach * pow(max(dot(n, normalize(v - dir)), 0.0), power));
	return s * amount;
}

float fade_pattern(vec2 pixel) {
	vec2 p = pixel + 5.588238 * mod(floor(TIME * 18.0), 64.0);
	return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}
