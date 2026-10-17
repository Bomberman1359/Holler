shader_type canvas_item;

uniform sampler2D strip : filter_linear;
uniform float heading = 0.0;
uniform float per = 2.9;
uniform float strip_w = 2090.0;
uniform float half_w = 230.0;
uniform vec2 rect_size = vec2(520.0, 56.0);
uniform float line_y = 32.0;
uniform float mark_x = 0.0;
uniform float mark_side = 0.0;
uniform float mark_on = 0.0;
uniform vec4 mark_color : source_color = vec4(1.0, 0.86, 0.6, 0.9);

float tri(vec2 p, vec2 tip, vec2 dir, float len, float half_base) {
	vec2 side = vec2(-dir.y, dir.x);
	float along = dot(p - tip, dir);
	float across = abs(dot(p - tip, side));
	if (along < 0.0 || along > len) {
		return 0.0;
	}
	return clamp(along * half_base / len - across + 0.5, 0.0, 1.0);
}

void fragment() {
	vec2 px = UV * rect_size;
	float x = px.x - rect_size.x * 0.5;
	float a = 0.0;
	if (abs(x) <= half_w) {
		float fade = clamp(1.0 - pow(abs(x) / half_w, 3.0), 0.0, 1.0);
		a = texture(strip, vec2(((heading + 180.0) * per + x) / strip_w, UV.y)).a * fade;
	}
	float m = 0.0;
	if (mark_on > 0.5) {
		if (mark_side == 0.0) {
			m = tri(px, vec2(rect_size.x * 0.5 + mark_x, line_y + 9.0), vec2(0.0, 1.0), 10.0, 6.0);
		} else {
			float cx = rect_size.x * 0.5 + mark_side * (half_w + 14.0);
			m = tri(px, vec2(cx + mark_side * 7.0, line_y), vec2(-mark_side, 0.0), 12.0, 7.0);
		}
	}
	m *= mark_color.a;
	vec3 rgb = mix(vec3(1.0), mark_color.rgb, m / max(m + a * (1.0 - m), 0.0001));
	COLOR = vec4(rgb, a + m * (1.0 - a));
}
