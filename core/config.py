def hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Unsupported color format: {value}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
SCREEN_TITLE = "Northern Light"

BACKGROUND_COLOR = hex_color("#020305")
FOG_COLOR = hex_color("#020305")
ACCENT_COLOR = hex_color("#A7C7D9")
WARNING_COLOR = hex_color("#8E98A3")
PLAYER_COLOR = hex_color("#D6DDE2")
ECHO_COLOR = hex_color("#DDEAF2")
ECHO_HAZE_COLOR = (*hex_color("#5C7385"), 45)

TILE = 64
WORLD_WIDTH = 12800
WORLD_HEIGHT = 4200

GRAVITY = 1.0
PLAYER_MOVE_SPEED = 8.5
PLAYER_ACCELERATION = 1.25
PLAYER_AIR_DRAG = 0.97
PLAYER_JUMP_SPEED = 16.5
PLAYER_MAX_FALL_SPEED = 26
PLAYER_JUMP_HOLD_TIME = 0.34
PLAYER_JUMP_HOLD_FORCE = 0.36
PLAYER_JUMP_CUT_FACTOR = 0.8

COYOTE_TIME = 0.12
JUMP_BUFFER_TIME = 0.14

CAMERA_LERP = 0.1
CAMERA_LOOKAHEAD = 170
CAMERA_WINDOW_WIDTH = 360
CAMERA_WINDOW_HEIGHT = 180

AMBIENT_PULSE_INTERVAL = 5.5
