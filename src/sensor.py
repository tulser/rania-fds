from typing import override, List
from dataclasses import dataclass

import logging

from fdscommon import FDSRoomConfig

import numpy as np
import rplidar


@dataclass
class SensorCalibration:
    """
    Calibration dataclass for representing
    """
    pass


@dataclass
class LidarCalibration(SensorCalibration):
    bounds: np.ndarray[float, float]


@dataclass
class RPLidarCalibration(LidarCalibration):
    pass


@dataclass
class SensorInfo:
    """
    Dataclass for sensor information necessary to load calibration data into
    the program.
    """

    location: str  # identifier for a sensor, should be persistent
    classtype: int
    devicetype: int
    calibration: SensorCalibration


class Sensor(object):
    """
    Abstract class for a generic sensor type.
    """

    _CLASS_TYPE: int
    _DEVICE_TYPE: int

    @property
    def classtype(cls):
        raise NotImplementedError

    @property
    def devicetype(cls):
        raise NotImplementedError


class Lidar(Sensor):
    """
    Abstract subclass for a generic LiDAR type.
    """

    _CLASS_TYPE = 1

    @override
    def classtype(cls):
        return cls._CLASS_TYPE


# TODO: Consider moving or adding driver/dependency code into this class to
#       avoid multiple instances of loggers.
class RPLidar(Lidar, rplidar.RPLidar):
    """
    Implementation for RPLidar devices.
    """

    _DEVICE_TYPE = 1

    def __init__(self, port: str, calibration: RPLidarCalibration,
                 baudrate: int = 115200, timeout: int = 1,
                 logger: logging.Logger = None):
        super().__init__(self, port, baudrate, timeout, logger)
        self._calibration = calibration
        self._logger = logger

    @override
    def devicetype(cls):
        return cls._DEVICE_TYPE


def getSensors(room_config: FDSRoomConfig,
               logger: logging.Logger) -> List[Sensor]:
    sensors = []
    for sensor in room_config.assigned_sensors:
        # TODO: This implementation is limited to using RPLidar and this code
        #       assumes as such. Future expansions to use multiple sensors of
        #      heterogenous device types or sensor classes should correct this.
        newsensor = RPLidar(sensor.location, sensor.calibration, logger)
        sensors.append(newsensor)
    return sensors
