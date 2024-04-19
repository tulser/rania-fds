from typing import Optional
from enum import Enum

from os.sys import realpath
import logging
import io
import sys

from .fdscommon import GlobalConfig, DomainConfig, RoomConfig
from .domain import Domain
import comm
from .sensor import getSensors


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFilter(logging.Filter):
    """
    Class for custom filtering behavior on Logger objects.
    """

    def __init__(self, logpath: Optional[str] = None):
        self.logpath = logpath

    def filter(record: logging.LogRecord):
        if record.level <= logging.INFO:
            sys.stdout.write(record.msg)
        else:
            sys.stderr.write(record.msg)


# DEFAULT_CONFIG_PATH_POSIX = "/etc/rania-fds/fds.conf"


def _getDefaultFDSConfig() -> GlobalConfig:
    """
    Get the base configuration for the FDS.

    :return: A basic global FDSGlobalConfig object.
    :rtype: FDSGlobalConfig
    """

    gc = GlobalConfig()
    gc.socket_path = f"./fds{0}".format(0)
    gc.dom_config = DomainConfig()
    # TODO: add more
    return gc


def _getFDSConfig(config_path: Optional[str], logger: logging.Logger
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
    :rtype: FDSGlobalConfig
    """

    logger.info("Loading FDS configuration")

    default_conf = _getDefaultFDSConfig()

    if config_path is None:
        return default_conf

    # TODO: Refactor to check multiple default paths (for different systems/
    #   distributions) to get a default configuration.

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
            return GlobalConfig()


def start(fds_config: GlobalConfig, logger: logging.Logger):
    """
    Start the fall detection system using the provided configuration.

    :param fds_config: Configuration for this FDS instance.
    :type fds_config: FDSGlobalConfig
    :param logger: Logger to use for logging throughout the FDS.
    :type logger: Logger
    """

    logger.info("Starting fall detection system.")
    socket_master = comm.FDSSocket(fds_config.sock_path, logger)
    sensors = getSensors(fds_config.sensors)

    domain = Domain(fds_config.dom_config, socket_master, logger)
    domain.start()
    return


def main(config_path: Optional[str] = None,
         loglevel: LogLevel = LogLevel.INFO):
    """
    True entry point for the fall detection system program.
    The configuration for the program is deserialized, parsed, and then used to
    start the fall detection system.

    :param config_path: A path to a config, overriding the
        default search paths.
    :type config_path: Optional[str]
    :param loglevel: The level to log events in the program.
    :type loglevel: FDSLogLevel
    """

    logger = logging.Logger("fds", loglevel)
    logger.addFilter(LogFilter())

    fds_config = _getFDSConfig(config_path, logger)

    start(fds_config, logger)
    return


if __name__ == "__main__":
    main()
