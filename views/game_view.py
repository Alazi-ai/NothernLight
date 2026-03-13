from __future__ import annotations

import math
from collections import defaultdict

import arcade

from core.config import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    CAMERA_LERP,
    CAMERA_LOOKAHEAD,
    CAMERA_WINDOW_HEIGHT,
    CAMERA_WINDOW_WIDTH,
    ECHO_COLOR,
    ECHO_HAZE_COLOR,
    FOG_COLOR,
    GRAVITY,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WARNING_COLOR,
)
from core.input_state import InputState
from entities.echo import EchoParticle
from entities.level_objects import EndingTrigger, ScanPickup
from entities.player import Player
from entities.unknown_entity import EntityScanMark, UnknownEntity
from views.ending_view import EndingView
from world.level import (
    build_double_jump_spawns,
    build_ending_spawns,
    build_entity_spawns,
    build_platforms,
    world_bounds,
)


class GameView(arcade.View):
    ECHO_COOLDOWN = 2.0
    ECHO_DISABLED_OUTLINE_COLOR = (210, 48, 48, 215)
    UNKNOWN_ENTITY_COLOR = (220, 48, 48, 235)
    UNKNOWN_ENTITY_ECHO_COLOR = (220, 64, 64)
    UNKNOWN_ENTITY_ECHO_HAZE_COLOR = (120, 24, 24, 45)
    UNKNOWN_ENTITY_ECHO_HIT_RADIUS = 54.0
    UNKNOWN_ENTITY_SCAN_REMOVE_RADIUS = 82.0
    UNKNOWN_ENTITY_CLEAR_SCAN_RADIUS = 120.0
    UNKNOWN_ENTITY_SCAN_MARK_LIFE = 5.0
    DOUBLE_JUMP_SCAN_COLOR = (255, 224, 110)
    DOUBLE_JUMP_HAZE_COLOR = (120, 102, 24, 45)
    DOUBLE_JUMP_MARK_LIFE = 4.0
    ENDING_WALK_SPEED = 48.0
    ENDING_DASH_SPEED = 1200.0
    ENDING_DASH_DELAY = 5.5

    def __init__(self) -> None:
        super().__init__(background_color=BACKGROUND_COLOR)
        self.player = Player()
        self.player.position = (180, 260)
        self.player_list: arcade.SpriteList[arcade.Sprite] = arcade.SpriteList()
        self.player_list.append(self.player)
        self.platforms = build_platforms()
        self.physics = arcade.PhysicsEnginePlatformer(
            self.player,
            walls=self.platforms,
            gravity_constant=GRAVITY,
        )
        self.camera: arcade.Camera2D | None = None
        self.gui_camera: arcade.Camera2D | None = None
        self.input_state = InputState()
        self.echoes: list[EchoParticle] = []
        self.unknown_entities = [
            UnknownEntity(x=spawn.x, y=spawn.y, width=spawn.width, height=spawn.height)
            for spawn in build_entity_spawns()
        ]
        self.double_jump_pickups = [
            ScanPickup(x=spawn.x, y=spawn.y, width=spawn.width, height=spawn.height)
            for spawn in build_double_jump_spawns()
        ]
        self.ending_triggers = [
            EndingTrigger(x=spawn.x, y=spawn.y, width=spawn.width, height=spawn.height)
            for spawn in build_ending_spawns()
        ]
        for entity in self.unknown_entities:
            entity.blocker_sprite = arcade.SpriteSolidColor(
                int(entity.width),
                int(entity.height),
                BACKGROUND_COLOR,
            )
            entity.blocker_sprite.position = (entity.x, entity.y)
            entity.scan_marks = []
            self.platforms.append(entity.blocker_sprite)
        self.echo_cooldown_remaining = 0.0
        self.cutscene_active = False
        self.cutscene_time = 0.0
        self.cutscene_entity: UnknownEntity | None = None
        self.world_left, self.world_right, self.world_bottom, self.world_top = world_bounds()

    def on_show_view(self) -> None:
        self.window.background_color = BACKGROUND_COLOR
        if hasattr(self.window, "ensure_background_music"):
            self.window.ensure_background_music()
        self.camera = arcade.Camera2D(window=self.window)
        self.gui_camera = arcade.Camera2D(window=self.window)

    def on_hide_view(self) -> None:
        if hasattr(self.window, "stop_echo_scan"):
            self.window.stop_echo_scan(save_progress=True)

    def on_draw(self) -> None:
        self.clear()
        if self.camera is None or self.gui_camera is None:
            return
        with self.camera.activate():
            self.draw_background()
            self.draw_world()
            self.draw_echoes()
            self.draw_unknown_entities()
            self.draw_double_jump_pickups()
            self.draw_cutscene_entity()
            self.draw_player_echo_cooldown()
            self.player_list.draw()
            self.draw_double_jump_indicator()
            self.draw_darkness()
        with self.gui_camera.activate():
            self.draw_ui()

    def on_update(self, delta_time: float) -> None:
        if hasattr(self.window, "update_echo_scan"):
            self.window.update_echo_scan()
        self.echo_cooldown_remaining = max(0.0, self.echo_cooldown_remaining - delta_time)

        if self.cutscene_active:
            self.update_cutscene(delta_time)
            return

        on_ground = self.physics.can_jump()
        self.player.update_timers(delta_time, on_ground)
        self.player.apply_horizontal_input(self.input_state.horizontal, on_ground)

        self.player.try_jump(on_ground)

        self.player.sustain_jump(delta_time, self.input_state.jump_held)

        if self.input_state.echo_pressed:
            if self.echo_cooldown_remaining <= 0.0:
                self.scan_nearby_revealed_entities()
                self.confirm_absent_entities_with_scan()
                self.emit_echo(self.player.center_x, self.player.center_y - 6, 0.95, "manual")
                self.echo_cooldown_remaining = self.ECHO_COOLDOWN
            elif hasattr(self.window, "play_echo_cancel"):
                self.window.play_echo_cancel()
            self.input_state.echo_pressed = False

        self.physics.update()
        self.prevent_surface_sliding()
        self.player.clamp_fall_speed()

        on_ground = self.physics.can_jump()
        self.player.register_air_state(on_ground)

        if self.player.intent_to_jump_cut and not self.input_state.jump_held:
            self.player.apply_jump_cut()

        for echo in self.echoes:
            if not self.is_echo_active_near_camera(echo, margin=520.0):
                continue
            echo.update(delta_time)
            self.process_echo_entity_interactions(echo)
            self.bounce_particle(echo)
        self.echoes = self.merge_stuck_echoes([echo for echo in self.echoes if echo.alive])
        self.update_entity_scan_marks(delta_time)
        self.update_double_jump_pickups(delta_time)
        self.check_ending_triggers()

        self.center_camera()
        self.keep_player_in_world()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self.cutscene_active:
            if symbol == arcade.key.DOWN:
                self.input_state.echo_pressed = True
            elif symbol == arcade.key.ESCAPE:
                from views.menu_view import MenuView

                self.window.show_view(MenuView())
            return
        if symbol == arcade.key.LEFT:
            self.input_state.left = True
        elif symbol == arcade.key.RIGHT:
            self.input_state.right = True
        elif symbol == arcade.key.UP:
            self.input_state.jump_held = True
            self.player.queue_jump()
        elif symbol == arcade.key.DOWN:
            self.input_state.echo_pressed = True
        elif symbol == arcade.key.ESCAPE:
            from views.menu_view import MenuView

            self.window.show_view(MenuView())

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if self.cutscene_active:
            return
        if symbol == arcade.key.LEFT:
            self.input_state.left = False
        elif symbol == arcade.key.RIGHT:
            self.input_state.right = False
        elif symbol == arcade.key.UP:
            self.input_state.jump_held = False
            self.player.intent_to_jump_cut = True

    def emit_echo(
        self,
        x: float,
        y: float,
        loudness: float,
        kind: str,
        scan_volume: float = 0.85,
    ) -> None:
        particle_count = {
            "step": 36,
            "jump": 60,
            "landing": 80,
            "ambient": 24,
            "manual": 148,
        }.get(kind, 40)
        speed = 145 + 135 * loudness
        life = (0.22 + 0.32 * loudness) * 3.2
        radius = 0.0

        if kind in {"manual", "cutscene"} and hasattr(self.window, "play_echo_scan"):
            self.window.play_echo_scan(volume=scan_volume)

        for index in range(particle_count):
            angle = math.tau * index / particle_count
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            self.echoes.append(
                EchoParticle(
                    x=x,
                    y=y,
                    prev_x=x,
                    prev_y=y,
                    velocity_x=velocity_x,
                    velocity_y=velocity_y,
                    life=life,
                    max_life=life,
                    radius=radius,
                    brightness=min(1.0, 0.78 + loudness * 0.22),
                    bounces_left=1,
                    stuck_radius=1.4 + loudness * 1.35,
                )
            )

    def bounce_particle(self, particle: EchoParticle) -> None:
        if particle.stuck or particle.bounces_left <= 0:
            return
        for sprite in self.platforms:
            if not (
                sprite.left <= particle.x <= sprite.right
                and sprite.bottom <= particle.y <= sprite.top
            ):
                continue
            overlap_left = abs(particle.x - sprite.left)
            overlap_right = abs(sprite.right - particle.x)
            overlap_bottom = abs(particle.y - sprite.bottom)
            overlap_top = abs(sprite.top - particle.y)
            smallest = min(overlap_left, overlap_right, overlap_bottom, overlap_top)
            stuck_to_wall = smallest in (overlap_left, overlap_right)
            if smallest == overlap_left:
                particle.x = sprite.left
            elif smallest == overlap_right:
                particle.x = sprite.right
            elif smallest == overlap_bottom:
                particle.y = sprite.bottom
            else:
                particle.y = sprite.top
            particle.velocity_x = 0.0
            particle.velocity_y = 0.0
            particle.stuck = True
            particle.stuck_to_wall = stuck_to_wall
            particle.bounces_left = 0
            if particle.stuck_to_wall:
                particle.life *= 10.4
                particle.max_life = particle.life
            else:
                particle.life *= 8.2
                particle.max_life = particle.life
            particle.brightness *= 0.95
            break

    def center_camera(self) -> None:
        if self.camera is None or self.gui_camera is None:
            return

        focus_x = self.player.center_x + self.player.facing * CAMERA_LOOKAHEAD
        focus_y = self.player.center_y + 40
        target_x = self.camera.position[0]
        target_y = self.camera.position[1]
        half_window_width = CAMERA_WINDOW_WIDTH / 2
        half_window_height = CAMERA_WINDOW_HEIGHT / 2

        if focus_x < target_x - half_window_width:
            target_x = focus_x + half_window_width
        elif focus_x > target_x + half_window_width:
            target_x = focus_x - half_window_width

        if focus_y < target_y - half_window_height:
            target_y = focus_y + half_window_height
        elif focus_y > target_y + half_window_height:
            target_y = focus_y - half_window_height

        camera_x = arcade.math.lerp(self.camera.position[0], target_x, CAMERA_LERP)
        camera_y = arcade.math.lerp(self.camera.position[1], target_y, CAMERA_LERP)
        half_width = SCREEN_WIDTH / 2
        half_height = SCREEN_HEIGHT / 2
        camera_x = max(self.world_left + half_width, min(self.world_right - half_width, camera_x))
        camera_y = max(self.world_bottom + half_height, min(self.world_top - half_height, camera_y))
        self.camera.position = (camera_x, camera_y)
        self.gui_camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def keep_player_in_world(self) -> None:
        if self.cutscene_active:
            return
        if self.player.center_y < self.world_bottom:
            self.player.position = (180, 260)
            self.player.change_x = 0
            self.player.change_y = 0
            self.echoes.clear()

    def process_echo_entity_interactions(self, particle: EchoParticle) -> None:
        for entity in self.unknown_entities:
            if not entity.active:
                continue
            if not self.particle_intersects_entity(particle, entity):
                continue
            entity.revealed = True
            if entity.blocker_sprite is not None:
                self.platforms.remove(entity.blocker_sprite)
                entity.blocker_sprite = None
            self.refresh_entity_scan_marks(entity, particle)
            particle.life = 0.0
            if hasattr(self.window, "play_unknown_entity_music"):
                self.window.play_unknown_entity_music()
            break
        for pickup in self.double_jump_pickups:
            if pickup.collected:
                continue
            if not self.particle_intersects_rect(particle, pickup.x, pickup.y, pickup.width, pickup.height):
                continue
            pickup.revealed = True
            self.add_scan_mark(
                pickup.scan_marks,
                pickup.x,
                pickup.y,
                pickup.width,
                pickup.height,
                particle,
                self.DOUBLE_JUMP_MARK_LIFE,
            )
            particle.life = 0.0
            break
        if self.cutscene_entity and self.particle_intersects_entity(particle, self.cutscene_entity):
            self.cutscene_entity.revealed = True
            self.add_scan_mark(
                self.cutscene_entity.scan_marks,
                self.cutscene_entity.x,
                self.cutscene_entity.y,
                self.cutscene_entity.width,
                self.cutscene_entity.height,
                particle,
                self.UNKNOWN_ENTITY_SCAN_MARK_LIFE,
            )
            particle.life = 0.0

    def scan_nearby_revealed_entities(self) -> None:
        for entity in self.unknown_entities:
            if not entity.active or not entity.revealed:
                continue
            if self.distance_between(
                self.player.center_x,
                self.player.center_y,
                entity.x,
                entity.y,
            ) > self.UNKNOWN_ENTITY_SCAN_REMOVE_RADIUS:
                continue
            entity.active = False
            entity.revealed = False
            entity.awaiting_clear_scan = True
            entity.removed_x = entity.x
            entity.removed_y = entity.y
            entity.scan_marks = []

    def confirm_absent_entities_with_scan(self) -> None:
        confirmed_any = False
        for entity in self.unknown_entities:
            if not entity.awaiting_clear_scan:
                continue
            if self.distance_between(
                self.player.center_x,
                self.player.center_y,
                entity.last_known_x,
                entity.last_known_y,
            ) > self.UNKNOWN_ENTITY_CLEAR_SCAN_RADIUS:
                continue
            entity.awaiting_clear_scan = False
            confirmed_any = True
        if confirmed_any and not any(
            entity.revealed or entity.awaiting_clear_scan
            for entity in self.unknown_entities
        ) and hasattr(self.window, "resume_background_music"):
            self.window.resume_background_music()

    def draw_background(self) -> None:
        left = self.camera.position[0] - SCREEN_WIDTH / 2
        bottom = self.camera.position[1] - SCREEN_HEIGHT / 2
        arcade.draw_rect_filled(
            arcade.LBWH(left, bottom, SCREEN_WIDTH, SCREEN_HEIGHT),
            BACKGROUND_COLOR,
        )

    def draw_world(self) -> None:
        for sprite in self.platforms:
            if any(entity.has_blocker(sprite) for entity in self.unknown_entities):
                continue
            left = sprite.left
            bottom = sprite.bottom
            width = sprite.width
            height = sprite.height
            color = (*BACKGROUND_COLOR[:3], 255)
            arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, color)

    def draw_echoes(self) -> None:
        for echo in self.echoes:
            if not self.is_echo_visible(echo, margin=140.0):
                continue
            color = (*ECHO_COLOR[:3], echo.alpha)
            haze = (*ECHO_HAZE_COLOR[:3], min(56, echo.alpha // 4))
            if echo.stuck:
                arcade.draw_circle_filled(echo.x, echo.y, echo.stuck_radius, color)
                continue
            arcade.draw_circle_filled(echo.x, echo.y, 1.8, color)
            arcade.draw_circle_filled(echo.x, echo.y, 3.2, haze)

    def draw_unknown_entities(self) -> None:
        for entity in self.unknown_entities:
            if not entity.active or not entity.revealed:
                continue
            for mark in entity.scan_marks or []:
                mark_color = (*self.UNKNOWN_ENTITY_ECHO_COLOR, mark.alpha)
                haze_color = (*self.UNKNOWN_ENTITY_ECHO_HAZE_COLOR[:3], min(80, mark.alpha // 2))
                arcade.draw_circle_filled(mark.x, mark.y, 2.2, mark_color)
                arcade.draw_circle_filled(mark.x, mark.y, 4.0, haze_color)

    def draw_double_jump_pickups(self) -> None:
        for pickup in self.double_jump_pickups:
            if pickup.collected or not pickup.revealed:
                continue
            for mark in pickup.scan_marks:
                alpha = mark.alpha
                mark_color = (*self.DOUBLE_JUMP_SCAN_COLOR, alpha)
                haze_color = (*self.DOUBLE_JUMP_HAZE_COLOR[:3], min(80, alpha // 2))
                arcade.draw_circle_filled(mark.x, mark.y, 2.0, mark_color)
                arcade.draw_circle_filled(mark.x, mark.y, 3.8, haze_color)

    def draw_double_jump_indicator(self) -> None:
        if not self.player.double_jump_available:
            return
        arcade.draw_circle_filled(
            self.player.center_x,
            self.player.top + 12,
            5,
            self.player.color,
        )

    def draw_cutscene_entity(self) -> None:
        if not self.cutscene_active or self.cutscene_entity is None:
            return
        left = self.cutscene_entity.x - self.cutscene_entity.width / 2
        right = self.cutscene_entity.x + self.cutscene_entity.width / 2
        bottom = self.cutscene_entity.y - self.cutscene_entity.height / 2
        top = self.cutscene_entity.y + self.cutscene_entity.height / 2
        steps = max(8, int(self.cutscene_entity.height / 8))
        for step in range(steps + 1):
            t = step / steps
            y = arcade.math.lerp(bottom, top, t)
            for x in (left, right):
                arcade.draw_circle_filled(x, y, 2.2, self.UNKNOWN_ENTITY_COLOR)
                arcade.draw_circle_filled(x, y, 4.0, (*self.UNKNOWN_ENTITY_ECHO_HAZE_COLOR[:3], 70))

    def distance_between(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x2 - x1, y2 - y1)

    def particle_intersects_rect(
        self,
        particle: EchoParticle,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
    ) -> bool:
        left = center_x - width / 2
        right = center_x + width / 2
        bottom = center_y - height / 2
        top = center_y + height / 2
        return left <= particle.x <= right and bottom <= particle.y <= top

    def rect_contains_point(
        self,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
        point_x: float,
        point_y: float,
    ) -> bool:
        left = center_x - width / 2
        right = center_x + width / 2
        bottom = center_y - height / 2
        top = center_y + height / 2
        return left <= point_x <= right and bottom <= point_y <= top

    def rects_overlap(
        self,
        center_x1: float,
        center_y1: float,
        width1: float,
        height1: float,
        center_x2: float,
        center_y2: float,
        width2: float,
        height2: float,
    ) -> bool:
        left1 = center_x1 - width1 / 2
        right1 = center_x1 + width1 / 2
        bottom1 = center_y1 - height1 / 2
        top1 = center_y1 + height1 / 2
        left2 = center_x2 - width2 / 2
        right2 = center_x2 + width2 / 2
        bottom2 = center_y2 - height2 / 2
        top2 = center_y2 + height2 / 2
        return left1 < right2 and right1 > left2 and bottom1 < top2 and top1 > bottom2

    def prevent_surface_sliding(self) -> None:
        if self.physics.can_jump():
            return
        if self.player.change_y >= 0.0:
            return
        next_left = self.player.left + self.player.change_x
        next_right = self.player.right + self.player.change_x
        for sprite in self.platforms:
            vertical_overlap = self.player.top > sprite.bottom and self.player.bottom < sprite.top
            horizontal_touch = abs(next_right - sprite.left) <= 2.0 or abs(next_left - sprite.right) <= 2.0
            if vertical_overlap and horizontal_touch:
                self.player.change_y = 0.0
                break

    def particle_intersects_entity(self, particle: EchoParticle, entity: UnknownEntity) -> bool:
        return self.particle_intersects_rect(particle, entity.x, entity.y, entity.width, entity.height)

    def add_scan_mark(
        self,
        marks: list,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
        particle: EchoParticle,
        life: float,
    ) -> None:
        left = center_x - width / 2
        right = center_x + width / 2
        bottom = center_y - height / 2
        top = center_y + height / 2
        overlap_left = abs(particle.x - left)
        overlap_right = abs(right - particle.x)
        overlap_bottom = abs(particle.y - bottom)
        overlap_top = abs(top - particle.y)
        smallest = min(overlap_left, overlap_right, overlap_bottom, overlap_top)

        hit_x = min(max(particle.x, left), right)
        hit_y = min(max(particle.y, bottom), top)
        if smallest == overlap_left:
            hit_x = left
        elif smallest == overlap_right:
            hit_x = right
        elif smallest == overlap_bottom:
            hit_y = bottom
        else:
            hit_y = top

        marks.append(
            EntityScanMark(
                x=hit_x,
                y=hit_y,
                life=life,
                max_life=life,
            )
        )

    def refresh_entity_scan_marks(self, entity: UnknownEntity, particle: EchoParticle) -> None:
        if entity.scan_marks is None:
            entity.scan_marks = []
        self.add_scan_mark(
            entity.scan_marks,
            entity.x,
            entity.y,
            entity.width,
            entity.height,
            particle,
            self.UNKNOWN_ENTITY_SCAN_MARK_LIFE,
        )

    def update_entity_scan_marks(self, delta_time: float) -> None:
        for entity in self.unknown_entities:
            if not entity.scan_marks:
                continue
            for mark in entity.scan_marks:
                mark.life = max(0.0, mark.life - delta_time)
            entity.scan_marks = [mark for mark in entity.scan_marks if mark.life > 0.0]
        if self.cutscene_entity and self.cutscene_entity.scan_marks:
            for mark in self.cutscene_entity.scan_marks:
                mark.life = max(0.0, mark.life - delta_time)
            self.cutscene_entity.scan_marks = [
                mark for mark in self.cutscene_entity.scan_marks if mark.life > 0.0
            ]

    def update_double_jump_pickups(self, delta_time: float) -> None:
        for pickup in self.double_jump_pickups:
            if pickup.collected:
                continue
            for mark in pickup.scan_marks:
                mark.life = max(0.0, mark.life - delta_time)
            pickup.scan_marks = [mark for mark in pickup.scan_marks if mark.life > 0.0]
            if not pickup.revealed:
                continue
            if not self.rect_contains_point(
                self.player.center_x,
                self.player.center_y,
                self.player.width,
                self.player.height,
                pickup.x,
                pickup.y,
            ):
                continue
            pickup.collected = True
            pickup.revealed = False
            pickup.scan_marks.clear()
            self.player.double_jump_unlocked = True
            self.player.double_jump_available = True
            if hasattr(self.window, "play_double_jump_collect"):
                self.window.play_double_jump_collect()

    def check_ending_triggers(self) -> None:
        if self.cutscene_active:
            return
        for trigger in self.ending_triggers:
            if trigger.triggered:
                continue
            if not self.rects_overlap(
                self.player.center_x,
                self.player.center_y,
                self.player.width,
                self.player.height,
                trigger.x,
                trigger.y,
                trigger.width,
                trigger.height,
            ):
                continue
            self.start_ending_cutscene(trigger)
            break

    def start_ending_cutscene(self, trigger: EndingTrigger) -> None:
        trigger.triggered = True
        self.cutscene_active = True
        self.cutscene_time = 0.0
        self.player.change_x = 0.0
        self.player.change_y = 0.0
        self.input_state.left = False
        self.input_state.right = False
        self.input_state.jump_held = False
        self.cutscene_entity = UnknownEntity(
            x=self.player.center_x - 640,
            y=trigger.y + 56,
            width=24,
            height=96,
            active=True,
            revealed=True,
            scan_marks=[],
        )
        if hasattr(self.window, "stop_all_music"):
            self.window.stop_all_music()
        if hasattr(self.window, "play_ending_music"):
            self.window.play_ending_music()

    def update_cutscene(self, delta_time: float) -> None:
        self.cutscene_time += delta_time
        self.player.change_x = 0.0
        self.player.change_y = 0.0
        if self.input_state.echo_pressed:
            self.emit_echo(self.player.center_x, self.player.center_y - 6, 0.7, "cutscene", scan_volume=0.12)
            self.input_state.echo_pressed = False
        self.physics.update()
        self.player.clamp_fall_speed()
        if self.cutscene_entity is not None:
            if self.cutscene_time < self.ENDING_DASH_DELAY:
                target_x = self.player.center_x - 180
                direction = 1 if self.cutscene_entity.x < target_x else -1
                self.cutscene_entity.x += direction * self.ENDING_WALK_SPEED * delta_time
            else:
                direction = 1 if self.cutscene_entity.x < self.player.center_x else -1
                self.cutscene_entity.x += direction * self.ENDING_DASH_SPEED * delta_time
            if self.distance_between(
                self.cutscene_entity.x,
                self.cutscene_entity.y,
                self.player.center_x,
                self.player.center_y,
            ) <= 36.0:
                self.window.show_view(EndingView())
                return
        for echo in self.echoes:
            if not self.is_echo_active_near_camera(echo, margin=520.0):
                continue
            echo.update(delta_time)
            self.process_echo_entity_interactions(echo)
            self.bounce_particle(echo)
        self.echoes = self.merge_stuck_echoes([echo for echo in self.echoes if echo.alive])
        self.update_entity_scan_marks(delta_time)
        self.center_camera()

    def draw_player_echo_cooldown(self) -> None:
        if self.echo_cooldown_remaining <= 0.0:
            return
        progress = self.echo_cooldown_remaining / self.ECHO_COOLDOWN
        width = self.player.width + 16 + 10 * progress
        height = self.player.height + 16 + 10 * progress
        arcade.draw_rect_outline(
            arcade.XYWH(
                self.player.center_x,
                self.player.center_y,
                width,
                height,
            ),
            self.ECHO_DISABLED_OUTLINE_COLOR,
            border_width=3 + 2 * progress,
            tilt_angle=0,
        )

    def is_echo_active_near_camera(self, echo: EchoParticle, margin: float) -> bool:
        if self.camera is None:
            return True
        left = self.camera.position[0] - SCREEN_WIDTH / 2 - margin
        right = self.camera.position[0] + SCREEN_WIDTH / 2 + margin
        bottom = self.camera.position[1] - SCREEN_HEIGHT / 2 - margin
        top = self.camera.position[1] + SCREEN_HEIGHT / 2 + margin
        return left <= echo.x <= right and bottom <= echo.y <= top

    def is_echo_visible(self, echo: EchoParticle, margin: float) -> bool:
        return self.is_echo_active_near_camera(echo, margin)

    def merge_stuck_echoes(self, echoes: list[EchoParticle]) -> list[EchoParticle]:
        merged: list[EchoParticle] = []
        stuck_groups: dict[tuple[int, int, bool], list[EchoParticle]] = defaultdict(list)
        grid_size = 10.0

        for echo in echoes:
            if not echo.stuck:
                merged.append(echo)
                continue
            key = (
                int(echo.x // grid_size),
                int(echo.y // grid_size),
                echo.stuck_to_wall,
            )
            stuck_groups[key].append(echo)

        for group in stuck_groups.values():
            if len(group) == 1:
                merged.append(group[0])
                continue

            total_weight = sum(max(0.1, echo.brightness) for echo in group)
            merged.append(
                EchoParticle(
                    x=sum(echo.x for echo in group) / len(group),
                    y=sum(echo.y for echo in group) / len(group),
                    prev_x=group[-1].prev_x,
                    prev_y=group[-1].prev_y,
                    velocity_x=0.0,
                    velocity_y=0.0,
                    life=max(echo.life for echo in group),
                    max_life=max(echo.max_life for echo in group),
                    radius=0.0,
                    brightness=min(1.0, total_weight / len(group) + 0.18 * (len(group) - 1)),
                    bounces_left=0,
                    stuck=True,
                    stuck_radius=min(5.2, max(echo.stuck_radius for echo in group) + 0.22 * (len(group) - 1)),
                    stuck_to_wall=group[0].stuck_to_wall,
                )
            )

        return merged

    def draw_darkness(self) -> None:
        left = self.camera.position[0] - SCREEN_WIDTH / 2
        bottom = self.camera.position[1] - SCREEN_HEIGHT / 2
        arcade.draw_rect_filled(
            arcade.LBWH(left, bottom, SCREEN_WIDTH, SCREEN_HEIGHT),
            (*FOG_COLOR[:3], 186),
        )

    def draw_ui(self) -> None:
        arcade.draw_text(
            "Стрелки влево и вправо — движение.",
            28,
            SCREEN_HEIGHT - 50,
            WARNING_COLOR,
            18,
        )
        arcade.draw_text(
            "Стрелка вверх — прыжок. Стрелка вниз — выпустить эхо.",
            28,
            SCREEN_HEIGHT - 78,
            (*ACCENT_COLOR[:3], 170),
            14,
        )
