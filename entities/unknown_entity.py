from __future__ import annotations

from dataclasses import dataclass

import arcade


@dataclass
class EntityScanMark:
    x: float
    y: float
    life: float
    max_life: float

    @property
    def alpha(self) -> int:
        if self.max_life <= 0.0:
            return 0
        fade = max(0.0, min(1.0, self.life / self.max_life))
        return int(255 * fade)


@dataclass
class UnknownEntity:
    x: float
    y: float
    width: float
    height: float
    blocker_sprite: arcade.Sprite | None = None
    active: bool = True
    revealed: bool = False
    awaiting_clear_scan: bool = False
    removed_x: float | None = None
    removed_y: float | None = None
    scan_marks: list[EntityScanMark] | None = None

    @property
    def last_known_x(self) -> float:
        return self.x if self.active else (self.removed_x or self.x)

    @property
    def last_known_y(self) -> float:
        return self.y if self.active else (self.removed_y or self.y)

    def has_blocker(self, sprite: arcade.Sprite) -> bool:
        return self.blocker_sprite is sprite
