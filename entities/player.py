from __future__ import annotations

import arcade

from core.config import (
    COYOTE_TIME,
    JUMP_BUFFER_TIME,
    PLAYER_ACCELERATION,
    PLAYER_AIR_DRAG,
    PLAYER_COLOR,
    PLAYER_JUMP_CUT_FACTOR,
    PLAYER_JUMP_HOLD_FORCE,
    PLAYER_JUMP_HOLD_TIME,
    PLAYER_JUMP_SPEED,
    PLAYER_MAX_FALL_SPEED,
    PLAYER_MOVE_SPEED,
)


class Player(arcade.SpriteSolidColor):
    def __init__(self) -> None:
        super().__init__(36, 72, PLAYER_COLOR)
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.facing = 1
        self.was_on_ground = False
        self.intent_to_jump_cut = False
        self.jump_hold_timer = 0.0
        self.double_jump_unlocked = False
        self.double_jump_available = False

    def queue_jump(self) -> None:
        self.jump_buffer_timer = JUMP_BUFFER_TIME

    def update_timers(self, delta_time: float, on_ground: bool) -> None:
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - delta_time)
        self.jump_hold_timer = max(0.0, self.jump_hold_timer - delta_time)
        if on_ground:
            self.coyote_timer = COYOTE_TIME
            if self.double_jump_unlocked:
                self.double_jump_available = True
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - delta_time)

    def apply_horizontal_input(self, direction: int, on_ground: bool) -> None:
        if direction:
            self.facing = direction
            self.change_x += direction * PLAYER_ACCELERATION
            self.change_x = max(-PLAYER_MOVE_SPEED, min(PLAYER_MOVE_SPEED, self.change_x))
        else:
            if on_ground:
                self.change_x = 0.0
            else:
                self.change_x *= PLAYER_AIR_DRAG
                if abs(self.change_x) < 0.05:
                    self.change_x = 0.0

    def try_jump(self, on_ground: bool) -> bool:
        if self.jump_buffer_timer <= 0.0:
            return False
        use_double_jump = not on_ground and self.coyote_timer <= 0.0
        if use_double_jump and not self.double_jump_available:
            return False
        self.change_y = PLAYER_JUMP_SPEED
        self.jump_buffer_timer = 0.0
        self.coyote_timer = 0.0
        self.intent_to_jump_cut = False
        self.jump_hold_timer = PLAYER_JUMP_HOLD_TIME
        if use_double_jump:
            self.double_jump_available = False
        return True

    def sustain_jump(self, delta_time: float, jump_held: bool) -> None:
        if not jump_held or self.jump_hold_timer <= 0.0 or self.change_y <= 0.0:
            return
        self.change_y += PLAYER_JUMP_HOLD_FORCE * delta_time * 60.0

    def apply_jump_cut(self) -> None:
        if self.change_y > 0 and self.jump_hold_timer > 0.0:
            self.change_y *= PLAYER_JUMP_CUT_FACTOR
        self.jump_hold_timer = 0.0
        self.intent_to_jump_cut = False

    def clamp_fall_speed(self) -> None:
        self.change_y = max(-PLAYER_MAX_FALL_SPEED, self.change_y)

    def register_air_state(self, on_ground: bool) -> tuple[bool, bool]:
        landed = on_ground and not self.was_on_ground
        left_ground = not on_ground and self.was_on_ground
        self.was_on_ground = on_ground
        return landed, left_ground
