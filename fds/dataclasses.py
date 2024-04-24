from typing import List, Callable, Any
from enum import IntEnum, auto
from dataclasses import dataclass

import numpy as np


class SensorClassType(IntEnum):
    LIDAR = auto()


class LidarDeviceType(IntEnum):
    RPLIDAR = auto()


@dataclass
class GlobalTrainingSets:
    clsf_lidar_knn_nkp: int
    clsf_lidar_knn_set_kpdata: List[np.ndarray]
    clsf_lidar_knn_set_labels: List[int]


@dataclass
class SensorInfo:
    """
    Dataclass for sensor information necessary to load calibration data into
    the program.
    """

    uid: int  # Unique, numeric identifier for the sensor
    path: str  # Resource identifier, should be persistent, unique
    classtype: int
    devicetype: int
    calibration_type: int
    calibration_path: str


@dataclass
class RoomCallbacks:
    event_cb: Callable[[int], Any]
    pushdata_cb: Callable[[int, np.ndarray, np.ndarray, List[np.ndarray]], Any]


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


@dataclass
class CalibrationData:
    pass


@dataclass
class BoundsCalibrationData(CalibrationData):
    arcsec_bounds: np.ndarray
