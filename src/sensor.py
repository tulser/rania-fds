from typing import override, List, Tuple
from abc import abstractmethod
from dataclasses import dataclass
from enum import IntEnum, auto

import logging

import numpy as np
import rplidar

from .fdscommon import FDSGlobalConfig, FDSRoomConfig


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


class LidarDeviceType(IntEnum):
    RPLIDAR = auto()


class Sensor(object):
    """
    Abstract class for a generic sensor type.
    """

    @property
    @classmethod
    @abstractmethod
    def classtype(cls) -> int:
        raise NotImplementedError

    @property
    @classmethod
    @abstractmethod
    def devicetype(cls) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
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

    @abstractmethod
    def getRawData(self) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def getFilteredData(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get filtered data from the sensor using the set calibration scheme for
        processing raw scan data.

        :return: A tuple of two ndarrays, (filtered data, culled data), with
                 shape (n, 2) and shape (m, 2) respectively.
        """

        raise NotImplementedError

    @abstractmethod
    def startScanning(self):
        raise NotImplementedError

    @abstractmethod
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
        self.__min_scan_len = min_scan_len
        self.__calibration = calibration
        self.__logger = logger

    @override
    @property
    @classmethod
    def devicetype(cls) -> int:
        return LidarDeviceType.RPLIDAR

    @override
    @property
    def calibration(self) -> RPLidarCalibration:
        return self.__calibration

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


_g_sensor_type_class_map: dict = {
    SensorClassType.LIDAR: {
        LidarDeviceType.RPLIDAR: RPLidar
    }
}


class FDSSensorTypeException(Exception):
    pass


def getSensors(sensors_info: List[SensorInfo], logger: logging.Logger
               ) -> List[Sensor]:
    """
    Initialize all sensors used by the FDS.

    :param List[SensorInfo] sensors_info: A list of SensorInfos with details
        for Initializing Sensors
    :param logging.Logger logger: A logger for logging errors.
    :return: A list of Sensors
    :rtype: List[Sensor]
    """
    global _g_sensor_type_class_map
    sensors_list = []
    for si in sensors_info:
        try:
            # Get the corresponding class from the map to construct
            cls: Sensor = _g_sensor_type_class_map[si.classtype][si.devicetype]
            sensor = cls(si.location, si.calibration, logger=logger)
            sensors_list.append(sensor)
        except KeyError:
            logger.error(f"Sensor info for `{0}` had bad class or device type."
                         .format(si.location))
            raise FDSSensorTypeException
    return sensors_list
