import arcade

from core.config import BACKGROUND_COLOR, SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from core.resources import resource_path
from views.menu_view import MenuView


class NorthernLightGame(arcade.Window):
    def __init__(self) -> None:
        super().__init__(
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            title=SCREEN_TITLE,
            antialiasing=True,
        )
        self.background_color = BACKGROUND_COLOR
        self.background_music = arcade.load_sound(resource_path("NORTHERNLIGHT.mp3"))
        self.unknown_entity_music = arcade.load_sound(resource_path("unknown-entity.mp3"))
        self.ending_music = arcade.load_sound(resource_path("ending.mp3"))
        self.double_jump_collect_sound = arcade.load_sound(resource_path("dj-collect.wav"))
        self.background_music_player = None
        self.unknown_entity_music_player = None
        self.ending_music_player = None
        self.echo_scan_sound = arcade.load_sound(resource_path("echo-scan.wav"))
        self.echo_cancel_sound = arcade.load_sound(resource_path("cancel.ogg"))
        self.echo_scan_player = None
        self.echo_scan_resume_time = 0.0
        self.echo_scan_started_at = 0.0
        self.echo_scan_duration = self.echo_scan_sound.get_length()
        self.show_view(MenuView())

    def ensure_background_music(self) -> None:
        if self.background_music_player is not None:
            return
        self.background_music_player = arcade.play_sound(self.background_music, volume=0.45, loop=True)

    def play_unknown_entity_music(self) -> None:
        self.stop_all_music()
        if self.unknown_entity_music_player is None:
            self.unknown_entity_music_player = arcade.play_sound(self.unknown_entity_music, volume=0.55, loop=True)

    def resume_background_music(self) -> None:
        self.stop_all_music()
        self.ensure_background_music()

    def play_ending_music(self) -> None:
        self.stop_all_music()
        if self.ending_music_player is None:
            self.ending_music_player = arcade.play_sound(self.ending_music, volume=0.65, loop=False)

    def play_echo_scan(self, volume: float = 0.85) -> None:
        self.stop_echo_scan(save_progress=True)
        self.echo_scan_player = arcade.play_sound(self.echo_scan_sound, volume=volume, loop=False)
        self.echo_scan_player.seek(self.echo_scan_resume_time)
        self.echo_scan_started_at = self.echo_scan_resume_time

    def update_echo_scan(self) -> None:
        if self.echo_scan_player is None:
            return
        played_time = self.echo_scan_player.time - self.echo_scan_started_at
        if played_time >= 1.0:
            self.stop_echo_scan(save_progress=True)

    def stop_echo_scan(self, save_progress: bool) -> None:
        if self.echo_scan_player is None:
            return
        if save_progress:
            self.echo_scan_resume_time = self.echo_scan_player.time % self.echo_scan_duration
        self.echo_scan_player.pause()
        self.echo_scan_player = None

    def play_echo_cancel(self) -> None:
        arcade.play_sound(self.echo_cancel_sound, volume=0.4, loop=False)

    def play_double_jump_collect(self) -> None:
        arcade.play_sound(self.double_jump_collect_sound, volume=0.8, loop=False)

    def stop_all_music(self) -> None:
        if self.background_music_player is not None:
            self.background_music_player.pause()
            self.background_music_player = None
        if self.unknown_entity_music_player is not None:
            self.unknown_entity_music_player.pause()
            self.unknown_entity_music_player = None
        if self.ending_music_player is not None:
            self.ending_music_player.pause()
            self.ending_music_player = None
