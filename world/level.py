from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import arcade

from core.config import BACKGROUND_COLOR, TILE, WORLD_HEIGHT, WORLD_WIDTH
from core.resources import resource_path

LEVEL_LAYOUT_PATH = Path(resource_path("world/level.txt"))
LEVEL_PLATFORM = "_"
LEVEL_ENTITY = "E"
LEVEL_DOUBLE_JUMP = "D"
LEVEL_ENDING = "N"
LEVEL_ROW_BORDER_LEFT = "["
LEVEL_ROW_BORDER_RIGHT = "]"
LEVEL_PLATFORM_HEIGHT = max(12, TILE // 4)
LEVEL_PLATFORM_Y_OFFSET = max(6, TILE // 8)
LEVEL_ENTITY_WIDTH = max(12, TILE // 3)
LEVEL_ENTITY_HEIGHT = TILE + TILE // 2
LEVEL_FLOOR_THICKNESS = 48
LEVEL_BOTTOM_MARGIN = 200
LEVEL_ROW_HEIGHT_FACTOR = 0.5
LEVEL_COLUMN_WIDTH_FACTOR = LEVEL_ROW_HEIGHT_FACTOR


@dataclass(frozen=True)
class LevelBlock:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class LevelEntitySpawn:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class LevelDoubleJumpSpawn:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class LevelEndingSpawn:
    x: float
    y: float
    width: float
    height: float


def make_block(x: float, y: float, width: float, height: float, color) -> arcade.SpriteSolidColor:
    sprite = arcade.SpriteSolidColor(int(width), int(height), color)
    sprite.center_x = x + width / 2
    sprite.center_y = y + height / 2
    return sprite


def load_level_rows() -> list[str]:
    rows: list[str] = []
    for raw_line in LEVEL_LAYOUT_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip("\n")
        if not line:
            continue
        if not (line.startswith(LEVEL_ROW_BORDER_LEFT) and line.endswith(LEVEL_ROW_BORDER_RIGHT)):
            raise ValueError(f"Invalid level row: {line!r}")
        rows.append(line)
    if not rows:
        raise ValueError("level.txt is empty")
    row_width = len(rows[0])
    if any(len(row) != row_width for row in rows):
        raise ValueError("All level.txt rows must have the same width")
    return rows


def cell_size(rows: list[str]) -> tuple[float, float]:
    row_count = len(rows)
    column_count = len(rows[0])
    return (
        (WORLD_WIDTH / column_count) * LEVEL_COLUMN_WIDTH_FACTOR,
        (WORLD_HEIGHT / row_count) * LEVEL_ROW_HEIGHT_FACTOR,
    )


def blocks_from_rows(rows: list[str]) -> list[LevelBlock]:
    blocks: list[LevelBlock] = []
    row_count = len(rows)
    cell_width, cell_height = cell_size(rows)

    for row_index, row in enumerate(rows):
        cell_bottom = (row_count - row_index - 1) * cell_height
        platform_y = cell_bottom + LEVEL_PLATFORM_Y_OFFSET
        run_start: int | None = None

        for column_index, cell in enumerate(row):
            if cell in (LEVEL_ROW_BORDER_LEFT, LEVEL_ROW_BORDER_RIGHT):
                wall_x = column_index * cell_width
                blocks.append(
                    LevelBlock(
                        x=wall_x,
                        y=cell_bottom,
                        width=cell_width,
                        height=cell_height,
                    )
                )
                if run_start is not None:
                    blocks.append(
                        LevelBlock(
                            x=run_start * cell_width,
                            y=platform_y,
                            width=(column_index - run_start) * cell_width,
                            height=LEVEL_PLATFORM_HEIGHT,
                        )
                    )
                    run_start = None
                continue
            is_platform = cell in (LEVEL_PLATFORM, LEVEL_ENTITY, LEVEL_DOUBLE_JUMP, LEVEL_ENDING)
            if is_platform and run_start is None:
                run_start = column_index
                continue
            if is_platform:
                continue
            if run_start is not None:
                blocks.append(
                    LevelBlock(
                        x=run_start * cell_width,
                        y=platform_y,
                        width=(column_index - run_start) * cell_width,
                        height=LEVEL_PLATFORM_HEIGHT,
                    )
                )
                run_start = None

        if run_start is not None:
            blocks.append(
                LevelBlock(
                    x=run_start * cell_width,
                    y=platform_y,
                    width=(len(row) - run_start) * cell_width,
                    height=LEVEL_PLATFORM_HEIGHT,
                )
            )

    return blocks


def entity_spawns_from_rows(rows: list[str]) -> list[LevelEntitySpawn]:
    spawns: list[LevelEntitySpawn] = []
    row_count = len(rows)
    cell_width, cell_height = cell_size(rows)

    for row_index, row in enumerate(rows):
        cell_bottom = (row_count - row_index - 1) * cell_height
        platform_y = cell_bottom + LEVEL_PLATFORM_Y_OFFSET
        for column_index, cell in enumerate(row):
            if cell != LEVEL_ENTITY:
                continue
            spawns.append(
                LevelEntitySpawn(
                    x=column_index * cell_width + cell_width / 2,
                    y=platform_y + LEVEL_PLATFORM_HEIGHT + LEVEL_ENTITY_HEIGHT / 2,
                    width=min(cell_width * 0.42, LEVEL_ENTITY_WIDTH),
                    height=LEVEL_ENTITY_HEIGHT,
                )
            )

    return spawns


def level_dimensions(rows: list[str]) -> tuple[float, float]:
    cell_width, cell_height = cell_size(rows)
    return len(rows[0]) * cell_width, len(rows) * cell_height


def double_jump_spawns_from_rows(rows: list[str]) -> list[LevelDoubleJumpSpawn]:
    spawns: list[LevelDoubleJumpSpawn] = []
    row_count = len(rows)
    cell_width, cell_height = cell_size(rows)

    for row_index, row in enumerate(rows):
        cell_bottom = (row_count - row_index - 1) * cell_height
        platform_y = cell_bottom + LEVEL_PLATFORM_Y_OFFSET
        for column_index, cell in enumerate(row):
            if cell != LEVEL_DOUBLE_JUMP:
                continue
            spawns.append(
                LevelDoubleJumpSpawn(
                    x=column_index * cell_width + cell_width / 2,
                    y=platform_y + LEVEL_PLATFORM_HEIGHT + TILE * 0.32,
                    width=min(cell_width * 0.5, TILE * 0.5),
                    height=min(cell_width * 0.5, TILE * 0.5),
                )
            )

    return spawns


def ending_spawns_from_rows(rows: list[str]) -> list[LevelEndingSpawn]:
    spawns: list[LevelEndingSpawn] = []
    row_count = len(rows)
    cell_width, cell_height = cell_size(rows)

    for row_index, row in enumerate(rows):
        cell_bottom = (row_count - row_index - 1) * cell_height
        platform_y = cell_bottom + LEVEL_PLATFORM_Y_OFFSET
        for column_index, cell in enumerate(row):
            if cell != LEVEL_ENDING:
                continue
            spawns.append(
                LevelEndingSpawn(
                    x=column_index * cell_width + cell_width / 2,
                    y=platform_y + LEVEL_PLATFORM_HEIGHT / 2,
                    width=cell_width,
                    height=LEVEL_PLATFORM_HEIGHT + TILE,
                )
            )

    return spawns


def build_platforms() -> arcade.SpriteList[arcade.Sprite]:
    rows = load_level_rows()
    blocks = blocks_from_rows(rows)
    world_width, _ = level_dimensions(rows)
    cell_width, _ = cell_size(rows)
    platforms: arcade.SpriteList[arcade.Sprite] = arcade.SpriteList(use_spatial_hash=True)

    for block in blocks:
        platforms.append(make_block(block.x, block.y, block.width, block.height, BACKGROUND_COLOR))

    for index in range(0, len(rows[0])):
        platforms.append(
            make_block(
                index * cell_width,
                -LEVEL_FLOOR_THICKNESS,
                cell_width,
                LEVEL_FLOOR_THICKNESS,
                BACKGROUND_COLOR,
            )
        )

    return platforms

def build_entity_spawns() -> list[LevelEntitySpawn]:
    return entity_spawns_from_rows(load_level_rows())


def build_double_jump_spawns() -> list[LevelDoubleJumpSpawn]:
    return double_jump_spawns_from_rows(load_level_rows())


def build_ending_spawns() -> list[LevelEndingSpawn]:
    return ending_spawns_from_rows(load_level_rows())


def world_bounds() -> tuple[float, float, float, float]:
    rows = load_level_rows()
    world_width, world_height = level_dimensions(rows)
    return 0, world_width, -LEVEL_BOTTOM_MARGIN, world_height + TILE
