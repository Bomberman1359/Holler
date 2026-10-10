shader_type spatial;
render_mode unshaded, fog_disabled, cull_back, blend_mix, depth_draw_never;

#include "res://shaders/night.gdshaderinc"

uniform sampler2D sheet : source_color, filter_linear_mipmap, repeat_disable;

varying vec3 wpos;
varying vec3 wn;
varying vec4 tint;
varying float sky;
varying float glow;
varying vec4 fog;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	tint = COLOR;
	sky = UV2.x;
	glow = UV2.y;
	fog = mist(CAMERA_POSITION_WORLD, wpos);
}

void fragment() {
	vec4 a = texture(sheet, UV);
	vec3 lit = a.rgb * tint.rgb * (night_light(wpos, normalize(wn), 0.0, sky) + vec3(glow * 3.0));
	ALBEDO = mix(lit, fog.rgb, fog.a);
	ALPHA = a.a * tint.a;
}
