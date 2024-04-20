import fdscommon

# Specific, persistent ID for RPLidar A1M8 (actually the UART bridge)
# FUTURE: Use configuration instead of using a hardcoded value
UDEV_RPLIDAR_SENSOR_ID = \
    "/dev/serial/by-id/" \
    "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
