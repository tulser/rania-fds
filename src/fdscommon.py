from typing import List, Tuple
from dataclasses import dataclass

import numpy as np

from .sensor import SensorInfo


class FDSException(Exception):
    """
    Generic exception for FDS-related errors, namely critical ones.
    """
    pass


@dataclass
class FDSRoomConfig:
    sensors_asid: List[str]


@dataclass
class FDSDomainConfig:
    room_configs: List[FDSRoomConfig]


@dataclass
class FDSGlobalConfig:
    socket_path: str
    sensors: List[SensorInfo]
    dom_config: FDSDomainConfig


@dataclass
class FDSGlobalTrainingSet:
    lidar_training: Tuple[np.ndarray, np.ndarray]
