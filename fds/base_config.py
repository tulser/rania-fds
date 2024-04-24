# This file serves to provide an implementation specific configuration
#   in `.serialization.getGlobalConfig`
# FUTURE: Delete this file in favor of mandating a specific schema in
#   `.serialization` with non-specific default fields.

from .dataclasses import GlobalConfig, DomainConfig, RoomConfig, SensorInfo, \
    SensorClassType, LidarDeviceType

# Specific, persistent ID for RPLidar A1M8 (actually the UART bridge)
# FUTURE: Use configuration instead of using a hardcoded value
UDEV_RPLIDAR_SENSOR_PATH = \
    "/dev/serial/by-id/" \
    "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"

TEST_SOCKET_DIR_POSIX = "./"
CALIBRATION_PATH = "./rplidar-1"


def basicConfig() -> GlobalConfig:
    gc = GlobalConfig(socket_dir="./")
    sensor = SensorInfo(uid=0,
                        path=UDEV_RPLIDAR_SENSOR_PATH,
                        classtype=SensorClassType.LIDAR,
                        devicetype=LidarDeviceType.RPLIDAR,
                        calibration_type=0,
                        calibration_path=CALIBRATION_PATH)
    gc.sensors = [sensor]

    dc = DomainConfig(uid=0)

    rc = RoomConfig(uid=0, sensors_assigned=[0])

    dc.room_configs = [rc]
    gc.dom_configs = [dc]
    return gc
