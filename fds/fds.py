from typing import Optional
from enum import IntEnum

import logging
from logging import Logger
import sys

from .domain import Domain
from .serialization import loadGlobalConfig, loadTrainingSets
from .sensor import getSensors


class FDSRootException(Exception):
    pass


class FDSRoot(object):
    """
    Root class for the fall detection system, should be instanced as a
    singleton.
    """

    def __init__(self, config_path: str, logger: Logger):
        """
        Initialize the fall detection system.

        :param fds_config: Configuration for this FDS instance.
        :type fds_config: FDSGlobalConfig
        :param logger: Logger to use for logging throughout the FDS.
        :type logger: Logger
        """

        fds_config = loadGlobalConfig(config_path, logger)
        training = loadTrainingSets(TEST_TRAINING_PATH_POSIX)

        sensors = getSensors(fds_config.sensors, logger)

        domains = []
        for dom_config in fds_config.dom_configs:
            domain = Domain(dom_config, self, training, sensors,
                            fds_config.socket_dir, logger)
            domains.append(domain)

        self.__domains = domains
        self.__config = fds_config
        self.__logger = logger
        return

    def start(self):
        """
        Start the fall detection system.
        """

        self.__logger.info("Starting fall detection system.")

        domains = self.__domains
        for domain in domains:
            domain.start()

        # FUTURE: Do not use `Domain.return_wait()`, use a Condition in this
        #   object, then pass to lower domains (and rooms) such that threads
        #   can decrement a counter and use the Condition to unblock (from this
        #   point in the function) when all threads exit.
        #   This loop is only here as a single domain instance is assumed.
        for domain in domains:
            domain.return_wait()
        return


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogHandler(logging.Handler):
    """
    Class for custom filtering behavior on Logger objects.
    """

    def __init__(self, loglevel: LogLevel, logpath: Optional[str] = None):
        super().__init__()
        self.__loglevel = loglevel
        self.__logpath = logpath

    def emit(self, record: logging.LogRecord):
        if (record.levelno <= logging.INFO):
            sys.stdout.write(record.msg)
        else:
            sys.stderr.write(record.msg)
        return


def getFDSLogger(loglevel: LogLevel) -> Logger:
    logger = logging.getLogger("fds")
    logger.setLevel(loglevel)
    logger.addHandler(LogHandler(loglevel))
    return logger


DEFAULT_CONFIG_PATH_POSIX = "/etc/rania-fds/fds.conf"
DEFAULT_CONFIG_BASE_PATH_POSIX = "/usr/share/rania-fds/fds.conf"
DEFAULT_TRAINING_PATH_POSIX = "/usr/share/rania-fds/training"

TEST_CONFIG_PATH_POSIX = "./fds.conf"
TEST_TRAINING_PATH_POSIX = "./training"

DEFAULT_LOGLEVEL = LogLevel.INFO


def main():
    """
    True entry point for the fall detection system program.
    The configuration for the program is deserialized, parsed, and then used to
    start the fall detection system.
    """

    # TODO: Use argparse module to parse passed options

    config_path = DEFAULT_CONFIG_BASE_PATH_POSIX
    loglevel = DEFAULT_LOGLEVEL

    logger = getFDSLogger(loglevel)

    fds = FDSRoot(config_path, logger)
    fds.start()
    return


if __name__ == "__main__":
    main()
