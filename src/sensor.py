from typing import List, Tuple, Dict, Optional
from abc import abstractmethod
from dataclasses import dataclass
from enum import IntEnum, auto

import logging

import numpy as np
import rplidar

from .serialization import getCalibration


@dataclass
class CalibrationData:
    pass


@dataclass
class BoundsCalibrationData(CalibrationData):
    arcsec_bounds: np.ndarray


class SensorCalibration(object):
    """
    Base calibration class
    """

    pass


class LidarCalibration(SensorCalibration):

    def filterFunc(self, points: np.ndarray):
        raise NotImplementedError


class RPLidarCalibration(LidarCalibration):
    pass


class BoundsFiltering(RPLidarCalibration):

    def __init__(self, data: BoundsCalibrationData):
        """
        :param bounds: Array of shape (n, 2), where the second dimension is
            structured in the format (a, b) where `a` is the end of the
            arc-interval, in units of degrees, and `b` is the distance bound
            for the interval.
            Arc-interval in the passed array is assumed to increase.
        :type bounds: np.ndarray
        """

        self._bounds = data.arcsec_bounds
        return

    @override
    def filterFunc(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        :param points: An array of polar points of shape (n, 2), where the
            second dimension is structured in the format (deg, dist) where
            `deg` is the angle, in units of degrees, and `dist` is the distance
            of a point.
            Points are assumed to be listed in increasing angle.
        :type points: np.ndarray
        """

        bounds = self._bounds
        unculled_list = []
        culled_list = []

        i = 0
        for p in points:
            # Go to next interval if the next point(s) exceed the arc
            if p[0] > bounds[i][0]:
                i += 1
            # For the selected interval, cull points if they are over the bound
            if p[1] > bounds[i][1]:
                culled_list.append(p)
            else:
                unculled_list.append(p)

        unculled = np.array(unculled_list)
        culled = np.array(culled_list)
        return (unculled, culled)


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
    def getRawSamples(self) -> np.ndarray:
        """
        Get a scan from the sensor.

        :return: A set of sample data with shape (n, 2), where samples are of
            the form (degree, distance), with `degree` in units of degrees of
            range [0-360), and `distance` in units of meters of range [0-inf).
            Both units are of type `float`
        :rtype: np.ndarray
        """

        raise NotImplementedError

    @abstractmethod
    def filterSamples(self, samples: np.ndarray
                      ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get filtered data using the set calibration scheme for
        processing the input, raw scan data.

        :param data: A list of scans to process.
        :type data: np.ndarray
        :return: A tuple with unculled and filtered/culled samples,
            respectively.
        :rtype: Tuple[np.ndarray, np.ndarray]
        """

        raise NotImplementedError

    @abstractmethod
    def startScanning(self):
        raise NotImplementedError

    @abstractmethod
    def stopScanning(self):
        raise NotImplementedError


class FDSCalibrationSupportError:
    pass


# FUTURE: Consider moving or adding driver/dependency code into this class
class RPLidar(Lidar, rplidar.RPLidar):
    """
    Implementation for RPLidar LiDAR devices.
    """

    _MIN_SCAN_LEN_DEFAULT = 5
    CALIBRATIONS_SUPPORT_MAP = {
        BoundsCalibrationData: BoundsFiltering
    }

    def __init__(self, sensor_info: SensorInfo,
                 calibration_data: Optional[CalibrationData],
                 logger: logging.Logger,
                 baudrate: int = 115200, timeout: int = 1,
                 min_scan_len: int = 5):
        self.__rpsup = super(rplidar.RPLidar, self)  # alias for RPL superclass
        self.__rpsup.__init__(self, sensor_info.path, baudrate, timeout,
                              logger)
        self.__min_scan_len = min_scan_len

        if calibration_data is not None:
            # Get corresponding class for instantiation with given calibration
            cls = None
            try:
                cls = self.CALIBRATIONS_SUPPORT_MAP[type(calibration_data)]
            except KeyError:
                logger.error(f"Given calibration for sensor `{0}` is not"
                             f"supported."
                             .format(sensor_info.uid))
                raise FDSCalibrationSupportError()
            self.__calibration = cls(calibration_data)

        self.__logger = logger

    @override
    @property
    @classmethod
    def devicetype(cls) -> int:
        return LidarDeviceType.RPLIDAR

    @override
    def getRawSamples(self) -> np.ndarray:
        scan = next(self.__iterator)
        scan_fv = [(deg, dist) for _, deg, dist in scan]
        return np.array(scan_fv)

    @override
    def filterSamples(self, samples: np.ndarray
                      ) -> Tuple[np.ndarray, np.ndarray]:
        return self.__calibration.filterFunc(samples)

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


SENSOR_TYPE_CLASS_MAP: dict = {
    SensorClassType.LIDAR: {
        LidarDeviceType.RPLIDAR: RPLidar
    }
}


class FDSSensorTypeException(Exception):
    """
    Exception class for raising errors related to bad indexing into
    `SENSOR_TYPE_CLASS_MAP`.
    """
    pass


def getSensors(sensors_info: List[SensorInfo], logger: logging.Logger
               ) -> Dict[Sensor]:
    """
    Initialize all sensors used by the FDS.

    :param List[SensorInfo] sensors_info: A list of SensorInfos with details
        for Initializing Sensors
    :param logging.Logger logger: A logger for logging errors.
    :return: A list of Sensors
    :rtype: Dict[Sensor]
    """

    global SENSOR_TYPE_CLASS_MAP

    sensors_dict = {}
    for si in sensors_info:
        if si.uid in sensors_dict:
            raise

        cls = None
        try:
            # Get the corresponding class from the map to construct
            cls: Sensor = SENSOR_TYPE_CLASS_MAP[si.classtype][si.devicetype]
        except KeyError:
            logger.error(f"Sensor info for `{0}` had bad class or device type."
                         .format(si.location))
            raise FDSSensorTypeException
        calibration_data = getCalibration(si, logger)
        sensor = cls(si.path, calibration_data, logger=logger)
        sensors_dict[si.uid] = sensor
    return sensors_dict
