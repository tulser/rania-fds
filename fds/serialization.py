from typing import Optional

import tomllib
import pickle
from logging import Logger

from .dataclasses import RoomConfig, DomainConfig, GlobalConfig, \
    GlobalTrainingSets, CalibrationData, BoundsCalibrationData, SensorInfo, \
    SensorClassType, LidarDeviceType
from .base_config import basicConfig


class FDSDeserialFormatError(Exception):
    pass


class FDSDeserialConfigError(Exception):
    pass


def _getBasicConfig() -> GlobalConfig:
    """
    Get the base configuration for the FDS.

    :return: A basic global FDSGlobalConfig object.
    :rtype: GlobalConfig
    """

    return basicConfig()


def loadGlobalConfig(config_path: Optional[str], logger: Logger
                     ) -> GlobalConfig:
    """
    Get the user-defined configuration for the FDS and apply it over the
    default configuration.

    :param config_path: A filesystem path to the file containing the system
        configuration, `None` to get the default config.
    :type config_path: Optional[str]
    :param logger: Logger to use for logging.
    :type logger: Logger
    :return: A global FDS configuration.
    :rtype: GlobalConfig
    """

    dgc = _getBasicConfig()
    if (config_path is None):
        logger.info("No config path provided. Using basic configuration.")
        return dgc
    return dgc  # TODO: Remove this return once config loading is implemented.

    # TODO: Implement configuration loading
    obj = None
    with open(config_path, "rb") as file:
        obj = tomllib.load(file)

    # Get global entries
    if "global" not in obj:
        raise FDSDeserialConfigError
    sec_global = obj["global"]
    g_socket_path = sec_global.get("socket_path", dgc.socket_path)

    return GlobalConfig()


CALIBRATION_MAP = {
    0: BoundsCalibrationData,
}


def loadCalibration(info: SensorInfo, logger: Logger) -> CalibrationData:
    """
    Called by sensor on construction
    """
    obj = None
    with open(info.calibration_path, "rb") as file:
        obj = pickle.load(file)

    expcls = CALIBRATION_MAP[info.calibration_type]
    if not isinstance(obj, expcls):
        logger.error(f"Incorrect calibration class {0} loaded. "
                     f"Expected {1}.".format(type(obj), expcls))
        raise FDSDeserialFormatError
    return obj


def loadTrainingSets(set_path: str, logger: Logger) -> GlobalTrainingSets:
    """
    Called in main
    """
    obj = None
    with open(set_path, "rb") as file:
        obj = pickle.load(file)

    if not isinstance(obj, GlobalTrainingSets):
        logger.error(f"Incorrect training set class {0} loaded. "
                     f"Expected {1}".format(type(obj), GlobalTrainingSets))
        raise FDSDeserialFormatError
    return obj
