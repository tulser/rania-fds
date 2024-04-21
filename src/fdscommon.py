from typing import List
from dataclasses import dataclass

from .sensor import SensorInfo


class FDSException(Exception):
    """
    Generic exception for FDS-related errors, namely critical ones.
    """
    pass


@dataclass
class RoomConfig:
    uid: int
    sensors_assigned: List[int]


@dataclass
class DomainConfig:
    uid: int
    room_configs: List[RoomConfig]


@dataclass
class GlobalConfig:
    socket_dir: str
    sensors: List[SensorInfo]
    dom_configs: List[DomainConfig]
