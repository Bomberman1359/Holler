extends RefCounted

const F_TANGENT := 1
const F_COLOR := 2
const F_UV2 := 4
const F_BONES := 8

static var _cache := {}


static func load_mesh(path: String, make_tangents := false, own_skin := false) -> Dictionary:
	var key := "%s|%s|%s" % [path, make_tangents, own_skin]
	if _cache.has(key):
		return _cache[key]
	var data := FileAccess.get_file_as_bytes(path)
	if data.size() < 24 or data.slice(0, 4).get_string_from_ascii() != "HMSH":
		push_error("not a mesh file: " + path)
		return {}
	var vcount := data.decode_u32(8)
	var icount := data.decode_u32(12)
	var flags := data.decode_u32(16)
	var bone_count := data.decode_u32(20)
	var at := 24
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _vec3(data.slice(at, at + vcount * 12).to_float32_array())
	at += vcount * 12
	arrays[Mesh.ARRAY_NORMAL] = _vec3(data.slice(at, at + vcount * 12).to_float32_array())
	at += vcount * 12
	arrays[Mesh.ARRAY_TEX_UV] = _vec2(data.slice(at, at + vcount * 8).to_float32_array())
	at += vcount * 8
	if flags & F_TANGENT:
		arrays[Mesh.ARRAY_TANGENT] = data.slice(at, at + vcount * 16).to_float32_array()
		at += vcount * 16
	if flags & F_COLOR:
		var raw := data.slice(at, at + vcount * 4)
		var cols := PackedColorArray()
		cols.resize(vcount)
		for i in vcount:
			cols[i] = Color8(raw[i * 4], raw[i * 4 + 1], raw[i * 4 + 2], raw[i * 4 + 3])
		arrays[Mesh.ARRAY_COLOR] = cols
		at += vcount * 4
	if flags & F_UV2:
		arrays[Mesh.ARRAY_TEX_UV2] = _vec2(data.slice(at, at + vcount * 8).to_float32_array())
		at += vcount * 8
	var format := 0
	if flags & F_BONES:
		if own_skin:
			var which := PackedFloat32Array()
			which.resize(vcount * 4)
			for i in vcount * 4:
				which[i] = float(data.decode_u16(at + i * 2))
			arrays[Mesh.ARRAY_CUSTOM0] = which
			at += vcount * 8
			arrays[Mesh.ARRAY_CUSTOM1] = data.slice(at, at + vcount * 16).to_float32_array()
			at += vcount * 16
			format = (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) | (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
		else:
			var bones := PackedInt32Array()
			bones.resize(vcount * 4)
			for i in vcount * 4:
				bones[i] = data.decode_u16(at + i * 2)
			arrays[Mesh.ARRAY_BONES] = bones
			at += vcount * 8
			arrays[Mesh.ARRAY_WEIGHTS] = data.slice(at, at + vcount * 16).to_float32_array()
			at += vcount * 16
	arrays[Mesh.ARRAY_INDEX] = data.slice(at, at + icount * 4).to_int32_array()
	at += icount * 4
	var skeleton: Array = []
	for b in bone_count:
		var n := data.decode_u16(at)
		at += 2
		var bone_name := data.slice(at, at + n).get_string_from_utf8()
		at += n
		var parent := data.decode_s32(at)
		at += 4
		var f := data.slice(at, at + 48).to_float32_array()
		at += 48
		skeleton.append({"name": bone_name, "parent": parent,
				"rest": Transform3D(Basis(Vector3(f[0], f[1], f[2]), Vector3(f[3], f[4], f[5]), Vector3(f[6], f[7], f[8])), Vector3(f[9], f[10], f[11]))})
	var mesh := ArrayMesh.new()
	if make_tangents and not (flags & F_TANGENT):
		var plain := ArrayMesh.new()
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var st := SurfaceTool.new()
		st.create_from(plain, 0)
		st.generate_tangents()
		mesh = st.commit()
	else:
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, format)
	var out := {"mesh": mesh, "bones": skeleton}
	_cache[key] = out
	return out


static func _vec3(f: PackedFloat32Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	var n := f.size() / 3
	out.resize(n)
	for i in n:
		out[i] = Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2])
	return out


static func _vec2(f: PackedFloat32Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	var n := f.size() / 2
	out.resize(n)
	for i in n:
		out[i] = Vector2(f[i * 2], f[i * 2 + 1])
	return out
