shader_type canvas_item;

uniform sampler2D grain_tex : repeat_enable, filter_linear;
uniform sampler2D dirt_tex : repeat_enable, filter_linear;
uniform vec2 res = vec2(960.0, 720.0);
uniform vec4 frame = vec4(0.0, 0.0, 1.0, 0.0);
uniform vec4 offsets = vec4(0.0);
uniform vec4 scratch = vec4(0.3, 0.7, 0.0, 0.0);
uniform float grain = 0.055;
uniform float saturation = 0.70;
uniform float scope = 0.0;
uniform float burn = 0.0;
uniform float worn = 0.0;
uniform float snow = 0.0;
uniform float jitter = 0.0;
uniform float exposure = 1.0;
uniform float dark = 0.0;

void fragment() {
	vec2 uv = UV + frame.xy;
	vec2 v = uv - 0.5;
	vec2 off = v * (0.006 + jitter * 0.03) + vec2(0.0011 + jitter * 0.004, 0.0);
	vec3 c = texture(TEXTURE, uv).rgb;
	vec3 c2 = texture(TEXTURE, uv + off).rgb;
	c = vec3(c2.r, mix(c.g, c2.g, 0.5), c.b) * exposure;
	float l = dot(c, vec3(0.299, 0.587, 0.114));

	float warm = clamp((c.r - max(c.g, c.b)) * 4.0 + (min(c.r, c.g) - c.b) * 2.0, 0.0, 1.0);
	vec3 film = mix(vec3(l), c, saturation - worn * 0.35 + warm * 0.35);
	film = film * 1.08 + vec3(0.026, 0.032, 0.048) * (1.0 - l);
	film = film * vec3(1.04, 1.0, 0.92) + vec3(0.0, 0.016, 0.026) * (1.0 - l);
	film = mix(film, film * vec3(1.1, 0.98, 0.8), worn);
	film = pow(max(film, vec3(0.0)), vec3(0.90));

	float ir = clamp(l * 3.2 + 0.05, 0.0, 1.0);
	c = mix(film, vec3(0.55, 1.0, 0.62) * ir, scope);

	vec3 g = texture(grain_tex, uv * res / 256.0 + offsets.xy).rgb - 0.5;
	float amount = grain + scope * 0.16 + worn * 0.08 + snow * 0.55;
	c += (g.r * 0.9 + g.g * 0.75) * amount * (0.55 + 0.9 * (1.0 - l));

	vec3 d = texture(dirt_tex, uv * vec2(1.6, 1.2) + offsets.zw).rgb;
	float dust = frame.w * (1.0 - scope);
	c *= 1.0 - d.r * dust * 0.75;
	c += d.g * dust * 0.3;

	float wob = sin(uv.y * 9.0 + scratch.x * 40.0) * 0.0015;
	float lines = smoothstep(0.0016, 0.0, abs(uv.x - scratch.x - wob)) * scratch.z
			+ smoothstep(0.0012, 0.0, abs(uv.x - scratch.y + wob)) * scratch.w;
	c += lines * 0.11 * (1.0 - scope);

	float vig = smoothstep(0.82, 0.28, length(v * vec2(1.0, 1.12)));
	c *= mix(0.42, 1.0, vig) * frame.z;
	float ring = smoothstep(0.47, 0.44, length(v * vec2(1.333, 1.0)));
	c *= mix(1.0, ring, scope);

	if (snow > 0.0) {
		float coarse = texture(grain_tex, uv * res / 700.0 + offsets.zw).g - 0.5;
		float band = smoothstep(0.92, 1.0, sin(uv.y * 23.0 + offsets.x * 60.0) * 0.5 + 0.5);
		c = mix(c, vec3(0.5 + coarse * 1.6), snow * (0.25 + 0.5 * band));
	}

	if (burn > 0.0) {
		float n = texture(dirt_tex, uv * 0.55 + 0.3).b * 0.6 + texture(grain_tex, uv * 1.7).b * 0.4;
		float b = smoothstep(1.0 - burn * 1.4, 1.0 - burn * 1.4 + 0.25, n + (0.5 - length(v)) * 0.6);
		c = mix(c, vec3(0.93, 0.93, 0.9), b);
		c = mix(c, vec3(1.0), smoothstep(0.7, 1.0, burn));
	}
	c *= 1.0 - dark;
	COLOR = vec4(clamp(c, 0.0, 1.0), 1.0);
}
