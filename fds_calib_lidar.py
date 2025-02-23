import pickle
import argparse
import logging
import math

from sklearn.cluster import DBSCAN
import numpy as np
import matplotlib.pyplot as plt

from fds.base_config import basicConfig
from fds.sensor import RPLidar
from fds.dataclasses import BoundsCalibrationData
from fds.util import convertPolarCartesian
from fds.fds import LogHandler, LogLevel


DEFAULT_SECTORS = 72

SCANS_MAX = 40
DBS_EPS_MM = 10. + (30. / (SCANS_MAX / 80))
DBS_MIN_SAMP = math.ceil(8 * SCANS_MAX / 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sensor", type=int, nargs=1, action="store")
    parser.add_argument("--nosave", "-d", action="store_true", default=False)
    parser.add_argument("--scannum", "-n", type=int, nargs="?",
                        default=SCANS_MAX)
    parser.add_argument("--eps", "-e", type=float, nargs="?",
                        default=DBS_EPS_MM)
    parser.add_argument("--minsamp", "-m", type=int, nargs="?",
                        default=DBS_MIN_SAMP)
    parser.add_argument("--sectors", "-s", type=int, nargs="?",
                        default=DEFAULT_SECTORS)
    parser.add_argument("--configpath", "-c", type=str, nargs="?",
                        default=None)

    args = parser.parse_args()

    logger = logging.getLogger("fds-calib")
    logger.setLevel(LogLevel.INFO)
    logger.addHandler(LogHandler(LogLevel.INFO))

    # TODO: Use arguments
    sensorid = 0  # Not used currently
    nosave = args.nosave
    scannum = args.scannum
    eps = args.eps
    minsamp = args.minsamp
    sectors = args.sectors
    # configpath = args.config  # Not used currently

    interval_size = 360.0 / sectors

    # Initialize sensor
    config = basicConfig()
    sensor = RPLidar(config.sensors[sensorid], None, logger)

    logger.info("Starting scan.\n")

    # Get scans of the environment
    sensor.startScanning()
    scan_list = []
    for i in range(0, scannum):
        scan = sensor.getRawSamples()
        scan_list.append(scan)
    sensor.stopScanning()

    logger.info("Got all scans: {0} scans made.\n".format(scannum))

    # Merge scans into one set
    scan_all = np.concatenate(scan_list, axis=0)

    # The array is sorted to make bounds calculation easier
    scan_all = scan_all[scan_all[:, 0].argsort()]

    logger.info("Removing noise.\n")

    # Use single set to remove noise
    scan_all_cart = convertPolarCartesian(scan_all)

    dbs = DBSCAN(eps=eps, min_samples=minsamp, metric="euclidean")
    labels = dbs.fit_predict(scan_all_cart)

    scan_all_fil = []
    for sample, label in zip(scan_all, labels):
        if (label != -1):
            scan_all_fil.append(sample)
    # Final scan with noise culled
    scan_final = np.array(scan_all_fil)

    logger.info("Generating bounds calibration.\n")

    # Calculate bounds
    bounds = []
    bs = 0
    ns = 0
    for i in range(0, sectors):
        interval_end = interval_size * (i + 1)
        # TODO: Find a way to vectorize or parallelize computation here
        while ns < len(scan_final):
            if scan_final[ns][0] >= interval_end:
                break
            ns += 1
        sample_slice = scan_final[bs:ns]
        # There is a chance for gaps. For empty slices, just use float infinity
        if len(sample_slice) == 0:
            bound = math.inf
        else:
            bound = sample_slice[:, 1].min()
        bounds.append([interval_end, bound])
        bs = ns
    bounds_np = np.array(bounds)
    calib_data = BoundsCalibrationData(arcsec_bounds=bounds_np)

    logger.info("Bounds calibration generated.\n")

    print(bounds_np)

    # Save the calibration
    if not nosave:
        calib_path = config.sensors[sensorid].calibration_path
        logger.info("Saving calibration to path \"{0}\".\n".format(calib_path))
        with open(calib_path, "wb") as file:
            pickle.dump(calib_data, file)
        logger.info("Saved calibration.\n")

    # Plot samples, including noise
    logger.info("Showing full scan plot.\n")
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.set_rmax(1000)
    ax.grid(True)
    ax.plot(np.radians(scan_all[:, 0]), scan_all[:, 1], 'o', color="red",
            markersize=2.5)
    ax.plot(np.radians(scan_final[:, 0]), scan_final[:, 1], 'o', color="blue",
            markersize=3.)
    plt.show(block=True)

    return


if __name__ == "__main__":
    main()
