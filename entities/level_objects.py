from __future__ import annotations

from dataclasses import dataclass, field

from entities.unknown_entity import EntityScanMark


@dataclass
class ScanPickup:
    x: float
    y: float
    width: float
    height: float
    collected: bool = False
    revealed: bool = False
    scan_marks: list[EntityScanMark] = field(default_factory=list)


@dataclass
class EndingTrigger:
    x: float
    y: float
    width: float
    height: float
    triggered: bool = False
