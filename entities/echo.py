from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class EchoParticle:
    x: float
    y: float
    prev_x: float
    prev_y: float
    velocity_x: float
    velocity_y: float
    life: float
    max_life: float
    radius: float
    brightness: float
    bounces_left: int
    stuck: bool = False
    stuck_radius: float = 2.2
    stuck_to_wall: bool = False

    def update(self, delta_time: float) -> None:
        self.prev_x = self.x
        self.prev_y = self.y
        if not self.stuck:
            self.x += self.velocity_x * delta_time
            self.y += self.velocity_y * delta_time
        self.life = max(0.0, self.life - delta_time)

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    @property
    def alpha(self) -> int:
        if not math.isfinite(self.life) or not math.isfinite(self.max_life) or not math.isfinite(self.brightness):
            return 0
        if self.max_life <= 0.0:
            return 0
        fade = self.life / self.max_life
        if not math.isfinite(fade):
            return 0
        return int(max(0.0, min(255.0, 255 * self.brightness * fade)))
