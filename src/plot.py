from typing import List

import threading

import matplotlib.pyplot as plt
import numpy as np


# ---- Old plotting code
def plot(x, y):
    plt.figure(figsize=(8, 6))

    colors = []
    for xi, yi in zip(x, y):
        if (-800 <= xi <= 1000) and (-2000 <= yi <= -500):
            colors.append('red')
        else:
            colors.append('blue')

    plt.scatter(x, y, c=colors, s=10)  # Customize color and size as needed
    plt.xlabel('X (mm)')
    plt.ylabel('Y (mm)')
    plt.title('LiDAR Scan')
    plt.grid(True)
    plt.axis('equal')  # Set aspect ratio to equal for square plot
    plt.show()


def testplot():
    data = []
    x = [coord[0] for coord in data]
    y = [coord[1] for coord in data]

    plot(x, y)
# ---- End Old plotting code


COLOR_PLOT_GEOM = "#383838"
COLOR_PLOT_NOISE = "#606060"

COLOR_PLOT_CLUSTER_MAP = [
    "#F012F3",
    "#23E4FF",
    "#E2F521",
    "#EF2345",
    "#26A0F1",
    "#54DF51",
]


class LidarPlotter(object):

    def __init__(self):
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
        ax.set_rmax(20)
        ax.set_rticks([])  # Less radial ticks
        ax.grid(True)

        self.__fig = fig
        self.__axes = ax

        self.__draw_event = threading.Event()
        self.__draw_get_lock = threading.Lock()
        self.__ret = False

        self.__thread = threading.Thread(target=self.__thread_plotLoop,
                                         name="FDS Visual Plotting Loop")
        return

    def __thread_plotLoop(self):
        # Alias plotting objects
        fig = self.__fig
        ax = self.__ax

        # Cache the background for blit
        background = fig.canvas.copy_from_bbox(ax.bbox)

        self.__draw_event.wait()

        fig.show(False)
        fig.draw()

        (points,) = ax.plot([], [], 'o', animated=True)

        # Enter the draw loop for further frames
        while self.__doloop:
            # Get data when available
            with self.__draw_get_lock:
                (geometry, noise, clusters) = self.__plot_input

            self.__draw_event.clear()

            # Plot data
            points.set_data(geometry)
            points.set_color(COLOR_PLOT_GEOM)
            ax.draw_artist(points)
            points.set_data(noise)
            points.set_color(COLOR_PLOT_NOISE)
            ax.draw_artist(points)
            for cluster, i in zip(clusters,
                                  range(0, len(COLOR_PLOT_CLUSTER_MAP))):
                points.set_data(cluster)
                points.set_color(
                    COLOR_PLOT_CLUSTER_MAP[i % len(COLOR_PLOT_CLUSTER_MAP)])
                ax.draw_artist(points)

            # (Re)draw the data
            fig.canvas.restore_region(background)
            ax.draw_artist(points)
            fig.canvas.blit(ax.bbox)

            fig.canvas.flush_events()

            # Wait for the next set of data
            self.__draw_event.wait()

        fig.set_visible(False)
        return

    def start(self):
        self.__doloop = True
        self.__draw_event.clear()
        self.__thread.run()
        return

    def stop(self):
        self.__doloop = False
        self.__draw_event.set()
        return

    def drawPlot(self, geometry: np.ndarray,
                 noise: np.ndarray,
                 clusters: List[np.ndarray]):
        """
        :param geometry: A filtered geometry sample set
        :type geometry: np.ndarray
        :param noise: A noise sample set
        :type noise: np.ndarray
        :param clusters: A list of clusters belonging to dynamic objects
        :type clusters: List[np.ndarray]
        """

        with self.__draw_get_lock:
            self.__plot_input = (geometry, noise, clusters)

        self.__draw_event.set()
        return
