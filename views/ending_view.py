import arcade

from core.config import ACCENT_COLOR, BACKGROUND_COLOR, SCREEN_HEIGHT, SCREEN_WIDTH


class EndingView(arcade.View):
    def __init__(self) -> None:
        super().__init__(background_color=BACKGROUND_COLOR)

    def on_show_view(self) -> None:
        self.window.background_color = BACKGROUND_COLOR

    def on_draw(self) -> None:
        self.clear()
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
            BACKGROUND_COLOR,
        )
        arcade.draw_text(
            "Спасибо за игру!",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2,
            ACCENT_COLOR,
            42,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
