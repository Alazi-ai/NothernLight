class InputState:
    def __init__(self) -> None:
        self.left = False
        self.right = False
        self.jump_held = False
        self.echo_pressed = False

    @property
    def horizontal(self) -> int:
        return int(self.right) - int(self.left)
