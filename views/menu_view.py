import math

import arcade

from core.config import ACCENT_COLOR, BACKGROUND_COLOR, SCREEN_HEIGHT, SCREEN_WIDTH, WARNING_COLOR


class MenuView(arcade.View):
    def __init__(self) -> None:
        super().__init__(background_color=BACKGROUND_COLOR)
        self.time = 0.0

    def on_show_view(self) -> None:
        self.window.background_color = BACKGROUND_COLOR
        if hasattr(self.window, "ensure_background_music"):
            self.window.ensure_background_music()

    def on_update(self, delta_time: float) -> None:
        self.time += delta_time

    def on_draw(self) -> None:
        self.clear()
        pulse = 0.5 + 0.5 * math.sin(self.time * 0.8)
        title_color = (*ACCENT_COLOR[:3], 200 + int(40 * pulse))
        hint_color = (*WARNING_COLOR[:3], 170 + int(50 * pulse))

        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
            BACKGROUND_COLOR,
        )
        arcade.draw_text(
            "NORTHERN LIGHT",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 + 110,
            title_color,
            56,
            anchor_x="center",
            font_name="Arial",
            bold=True,
        )
        arcade.draw_text(
            "Пройди этот тёмный путь",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 + 42,
            WARNING_COLOR,
            18,
            anchor_x="center",
            italic=True,
        )
        arcade.draw_text(
            "← / → движение    ↑ прыжок    ESC меню    ↓ выпустить эхо",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 - 60,
            hint_color,
            20,
            anchor_x="center",
        )
        arcade.draw_text(
            "Нажми любую клавишу",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 - 130,
            hint_color,
            24,
            anchor_x="center",
        )

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        from views.game_view import GameView

        self.window.show_view(GameView())

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        from views.game_view import GameView

        self.window.show_view(GameView())
