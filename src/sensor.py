from typing import (override, List)
from dataclasses import dataclass
from enum import IntEnum, auto

import logging

import numpy as np
import rplidar

from fdscommon import (FDSDomainConfig, FDSRoomConfig)


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


class SensorClassType(IntEnum):
    LIDAR = auto()


class SensorDeviceType(IntEnum):
    pass


class LidarDeviceType(IntEnum):
    RPLIDAR = auto()


class Sensor(object):
    """
    Abstract class for a generic sensor type.
    """

    @property
    @classmethod
    def classtype(cls) -> int:
        raise NotImplementedError

    @property
    @classmethod
    def devicetype(cls) -> int:
        raise NotImplementedError

    @property
    def calibration(self) -> SensorCalibration:
        raise NotImplementedError


class Lidar(Sensor):
    """
    Abstract subclass for a generic LiDAR type.
    """

    @override
    @property
    @classmethod
    def classtype(cls) -> int:
        return SensorClassType.LIDAR

    def gerRawData(self) -> np.ndarray:
        raise NotImplementedError

    def getFilteredData(self) -> (np.ndarray, np.ndarray):
        """
        Get filtered data from the sensor using the set calibration scheme for
        processing raw scan data.

        :return: A tuple of two ndarrays, (filtered data, culled data), with
                 shape (n, 2) and shape (m, 2) respectively.
        """

        raise NotImplementedError

    def startScanning(self):
        raise NotImplementedError

    def stopScanning(self):
        raise NotImplementedError


# TODO: Consider moving or adding driver/dependency code into this class
class RPLidar(Lidar, rplidar.RPLidar):
    """
    Implementation for RPLidar devices.
    """

    _MIN_SCAN_LEN_DEFAULT = 5

    def __init__(self, port: str, calibration: RPLidarCalibration,
                 baudrate: int = 115200, timeout: int = 1,
                 min_scan_len: int = 5,
                 logger: logging.Logger = None):
        self.__rpsup = super(rplidar.RPLidar, self)  # alias for RPL superclass
        self.__rpsup.__init__(self, port, baudrate, timeout, logger)
        self._min_scan_len = min_scan_len
        self._calibration = calibration
        self._logger = logger

    @override
    @property
    @classmethod
    def devicetype(cls) -> int:
        return LidarDeviceType.RPLIDAR

    @override
    @property
    def calibration(self) -> RPLidarCalibration:
        return self._calibration

    @override
    def getRawData(self) -> np.ndarray:
        scan = next(self.__iterator)
        scan_fv = [(deg, dist) for _, deg, dist in scan]
        return np.array(scan_fv)

    @override
    def getFilteredData(self) -> (np.ndarray, np.ndarray):
        scan = self.getRawData()
        # TODO: Implement filtering
        return (scan, scan)

    @override
    def startScanning(self):
        if self.__iterator is None:
            self.__iterator = self.__rpsup.iter_scans(
                min_len=self._min_scan_len)
        self.__rpsup.start_motor()
        self.__rpsup.start()

    @override
    def stopScanning(self):
        self.__rpsup.stop_motor()
        self.__rpsup.stop()


def findSensors(logger: logging.Logger):
    """
    Scan for supported sensors attached or connected to the localhost.
    """
    raise NotImplementedError


def getSensors(dom_config: FDSDomainConfig, logger: logging.Logger):
    """
    Initialize all sensors allocated to a domain.
    """
    pass


def getRoomSensors(room_config: FDSRoomConfig,
                   logger: logging.Logger) -> List[Sensor]:
    """
    Get sensors allocated to a room.

    :return: A list of initialized sensor objects corresponding to the those
             listed in the given configuration.
    """
    sensors = []
    for sensor in room_config.assigned_sensors:
        # TODO: This implementation is limited to using RPLidar and this code
        #       assumes as such. Future expansions to use multiple sensors of
        #       heterogenous models or sensor classes should correct this.
        newsensor = RPLidar(sensor.location, sensor.calibration, logger)
        sensors.append(newsensor)
    return sensors
