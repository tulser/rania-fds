from typing import Optional
from enum import Enum

import logging
import sys

from .algs import GlobalTrainingSets
from .fdscommon import GlobalConfig, DomainConfig, RoomConfig
from .domain import Domain
from .ipc import Socket
import serialization
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


def start(fds_config: GlobalConfig, training: GlobalTrainingSets,
          logger: logging.Logger):
    """
    Start the fall detection system using the provided configuration.

    :param fds_config: Configuration for this FDS instance.
    :type fds_config: FDSGlobalConfig
    :param logger: Logger to use for logging throughout the FDS.
    :type logger: Logger
    """

    logger.info("Starting fall detection system.")
    socket_master = Socket(fds_config.socket_dir, logger)
    sensors = getSensors(fds_config.sensors, logger)

    domains = []
    for dom_config in fds_config.dom_configs:
        domain = Domain(dom_config, training, sensors, socket_master, logger)
        domains.append(domain)

    for domain in domains:
        domain.start()
    return


DEFAULT_CONFIG_PATH_POSIX = "/etc/rania-fds/fds.conf"
DEFAULT_CONFIG_BASE_PATH_POSIX = "/usr/share/rania-fds/fds.conf"
DEFAULT_TRAINING_PATH_POSIX = "/usr/share/rania-fds/training"

TEST_CONFIG_PATH_POSIX = "./fds.conf"
TEST_TRAINING_PATH_POSIX = "./training"


def main():
    """
    True entry point for the fall detection system program.
    The configuration for the program is deserialized, parsed, and then used to
    start the fall detection system.
    """

    config_path = DEFAULT_CONFIG_BASE_PATH_POSIX
    loglevel = LogLevel.INFO

    logger = logging.Logger("fds", loglevel)
    logger.addFilter(LogFilter())

    fds_config = serialization.getGlobalConfig(config_path, logger)
    training = serialization.getTrainingSets(TEST_TRAINING_PATH_POSIX)

    start(fds_config, training, logger)
    return


if __name__ == "__main__":
    main()
