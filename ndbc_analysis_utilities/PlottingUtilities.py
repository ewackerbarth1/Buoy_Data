import numpy as np
import matplotlib.cm as cmx

def makeCircularHist(ax, x, bins=16, density=True, offset=0, gaps=True) -> tuple:
    """
    Produce a circular histogram of angles on ax.
    copied from https://stackoverflow.com/questions/22562364/circular-polar-histogram-in-python

    Parameters
    ----------
    ax : matplotlib.axes._subplots.PolarAxesSubplot
        axis instance created with subplot_kw=dict(projection='polar').

    x : array
        Angles to plot, expected in units of radians.

    bins : int, optional
        Defines the number of equal-width bins in the range. The default is 16.

    density : bool, optional
        If True plot frequency proportional to area. If False plot frequency
        proportional to radius. The default is True.

    offset : float, optional
        Sets the offset for the location of the 0 direction in units of
        radians. The default is 0.

    gaps : bool, optional
        Whether to allow gaps between bins. When gaps = False the bins are
        forced to partition the entire [-pi, pi] range. The default is True.

    Returns
    -------
    n : array or list of arrays
        The number of values in each bin.

    bins : array
        The edges of the bins.

    patches : `.BarContainer` or list of a single `.Polygon`
        Container of individual artists used to create the histogram
        or list of such containers if there are multiple input datasets.
    """
    # Wrap angles to [-pi, pi)
    x = (x+np.pi) % (2*np.pi) - np.pi

    # Force bins to partition entire circle
    if not gaps:
        bins = np.linspace(-np.pi, np.pi, num=bins+1)

    # Bin data and record counts
    n, bins = np.histogram(x, bins=bins)

    # Compute width of each bin
    widths = np.diff(bins)

    # By default plot frequency proportional to area
    if density:
        # Area to assign each bin
        area = n / x.size
        # Calculate corresponding bin radius
        radius = (area/np.pi) ** .5
    # Otherwise plot frequency proportional to radius
    else:
        radius = n

    # Plot data on ax
    patches = ax.bar(bins[:-1], radius, zorder=1, align='edge', width=widths,
                     edgecolor='black', fill=False, linewidth=1)  # edgecolor='c0'

    # Set the direction of the zero angle
    ax.set_theta_offset(offset)

    # Remove ylabels for area plots (they are mostly obstructive)
    if density:
        ax.set_yticks([])

    return n, bins, patches

def convertTimestampsToTimedeltas(timestamps: np.ndarray[np.datetime64]) -> np.ndarray[np.float64]:
    now = np.datetime64('now')
    deltas = now - timestamps
    deltaMins = deltas.astype('timedelta64[m]')
    deltaHrs = -1 * deltaMins.astype('float') / 60
    return deltaHrs 

def getColors(timeDeltas: np.ndarray, scalarMap: cmx.ScalarMappable) -> list[tuple]:
    # map time deltas to [0, 1] 
    maxTime = max(timeDeltas)
    minTime = min(timeDeltas)
    colors = [scalarMap.to_rgba((x - minTime) / (maxTime - minTime)) for x in timeDeltas]
    return colors 

