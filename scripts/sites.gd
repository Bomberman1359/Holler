extends RefCounted

const SPAWN := Vector2(-200, 1213)
const GASTHAUS := Vector2(-175, 888)
const CHURCH := Vector2(-90, 638)
const CHURCH_ROOF := Vector2(70, 560)
const BOMBER := Vector2(-575, 338)
const VIADUCT := Vector2(-150, 150)
const SANATORIUM := Vector2(-440, -112)
const FORD := Vector2(-165, -312)
const RADAR := Vector2(100, -487)
const TUNNEL := Vector2(275, -887)
const LOOKOUT := Vector2(900, -1212)

const FOOTPRINTS := [
	[Vector2(-232, 548), 0.95, 1.0],
	[Vector2(-292, 478), 0.95, -1.0],
	[Vector2(-372, 428), 0.95, 1.0],
]
const FOOT_LENGTH := 46.0
const FOOT_WIDTH := 18.0

const LANES := [
	[Vector2(300, 940), Vector2(-150, 250)],
	[Vector2(-470, 700), Vector2(-250, -120)],
	[Vector2(40, -90), Vector2(600, -520)],
	[Vector2(-320, -480), Vector2(110, -1150)],
]
const LANE_HALF_WIDTH := 5.0

const TRACK := [
	Vector2(-200, 1213), Vector2(-178, 1040), Vector2(-170, 933), Vector2(-169, 843), Vector2(-125, 735),
	Vector2(-100, 663), Vector2(-112, 596), Vector2(-215, 500), Vector2(-330, 415), Vector2(-470, 372),
	Vector2(-562, 352), Vector2(-545, 250), Vector2(-470, 150), Vector2(-462, 20), Vector2(-447, -82),
	Vector2(-370, -205), Vector2(-250, -285), Vector2(-165, -318), Vector2(-70, -390), Vector2(20, -365),
	Vector2(120, -385), Vector2(158, -450), Vector2(108, -480), Vector2(150, -600), Vector2(190, -740),
	Vector2(262, -850), Vector2(240, -960), Vector2(330, -1110), Vector2(520, -1215), Vector2(720, -1245),
	Vector2(885, -1206),
]
const TRACK_STOPS := [3, 5, 10, 14, 22, 25, 30]
const TRACK_HALF_WIDTH := 2.2


static func old(v: Vector2) -> Vector2:
	return v * 0.5 - Vector2(50, 137)
