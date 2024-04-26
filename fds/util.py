import numpy as np


def convertPolarCartesian(pts: np.ndarray) -> np.ndarray:
    pts = pts.copy()
    x = pts[:, 1] * np.cos(np.radians(pts[:, 0]))
    y = pts[:, 1] * np.sin(np.radians(pts[:, 0]))
    return np.array((x, y)).transpose()
