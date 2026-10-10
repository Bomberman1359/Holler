shader_type spatial;
render_mode unshaded, fog_disabled, blend_add, depth_draw_never, cull_disabled;

varying float life;

void vertex() {
	vec3 center = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float d = distance(center, CAMERA_POSITION_WORLD);
	float pulse = 0.55 + 0.45 * sin(TIME * 2.4 + INSTANCE_CUSTOM.y * 6.283);
	life = INSTANCE_CUSTOM.x * pulse * smoothstep(17.0, 8.0, d) * smoothstep(0.4, 1.4, d);
	float size = 0.035 + 0.011 * d;
	vec3 right = INV_VIEW_MATRIX[0].xyz;
	vec3 up = INV_VIEW_MATRIX[1].xyz;
	vec3 at = center + (right * VERTEX.x + up * VERTEX.y) * size;
	POSITION = PROJECTION_MATRIX * (VIEW_MATRIX * vec4(at, 1.0));
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float soft = smoothstep(1.0, 0.0, length(p));
	float rays = smoothstep(0.10, 0.0, abs(p.x)) * smoothstep(1.0, 0.0, abs(p.y)) + smoothstep(0.10, 0.0, abs(p.y)) * smoothstep(1.0, 0.0, abs(p.x));
	ALBEDO = vec3(1.0, 0.97, 0.9) * (soft * soft * 0.6 + rays * 0.8) * life;
}
