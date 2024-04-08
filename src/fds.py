from typing import Optional
from enum import Enum

from os.sys import realpath
import logging
import io
import sys
import pickle

from .fdscommon import FDSGlobalConfig, FDSDomainConfig, FDSRoomConfig, \
    FDSException
from .domain import FDSDomain
import comm
from .sensor import getSensors


class FDSLogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class FDSLogFilter(logging.Filter):
    def __init__(self, logpath: Optional[str] = None):
        self.logpath = logpath

    def filter(record: logging.LogRecord):
        if record.level <= logging.WARNING:
            sys.stdout.write(record.msg)
        else:
            sys.stderr.write(record.msg)


# Use for testing
DEFAULT_CONFIG_PATH_POSIX = "/etc/rania-fds/fds.conf"


def _getFDSConfig(config_path: str, logger: logging.Logger) -> FDSGlobalConfig:
    try:
        config_path = realpath(config_path)
    except Exception as err:
        logger.error(f"Cannot open config file at path \"{0}\": {1}"
                     .format(config_path, err))
        raise err

    try:
        fds_file = io.open(config_path, 'rb')
    except Exception as err:
        raise err
    else:
        with fds_file:
            # TODO: Parse fds config
            # NOTE: For this implementation, we assume there is one domain that
            #       is equivalent to the FDS, i.e, a domain represents an FDS
            return FDSGlobalConfig()


def _getDefaultFDSConfig() -> FDSGlobalConfig:
    """
    Get the base configuration for the fall detection system

    :return: A basic global FDS configuration object.
    :rtype: FDSGlobalConfig
    """

    gc = FDSGlobalConfig()
    gc.socket_path = f"./fds{0}".format(0)
    gc.dom_config = FDSDomainConfig()


def startFDS(fds_config: FDSGlobalConfig, logger: logging.Logger):
    """
    Start the fall detection system using the provided configuration.
    """

    logger.info("Starting fall detection system.")
    socket_master = comm.FDSSocket(fds_config.sock_path, logger)
    sensors = getSensors(fds_config.sensors)

    domain = FDSDomain(fds_config.dom_config, socket_master, logger)
    domain.start()
    return


def main(config_path: Optional[str] = None,
         loglevel: FDSLogLevel = FDSLogLevel.INFO):
    """
    True entry point for the fall detection system program.
    The configuration for the program is deserialized, parsed, and then used to
    start the fall detection system.

    :param Optional[str] config_path: A path to a config, overriding the
        default search paths.
    :param FDSLogLevel loglevel: The level to log events in the program.
    """

    logger = logging.Logger("fds", loglevel)
    logger.addFilter(FDSLogFilter())

    fds_config = _getDefaultFDSConfig()

    # TODO: Get and parse config from filesystem, potentially to overwrite
    #       aspects of the default config.
    # if config_path is None:
    #     # TODO: Refactor to check multiple paths (for different systems/
    #     #       distributions) or rework for a database
    #     fds_config = _getFDSConfig(DEFAULT_CONFIG_PATH_POSIX)
    # else:
    #     fds_config = _getFDSConfig(config_path)

    startFDS(fds_config, logger)
    return


if __name__ == "__main__":
    main()
