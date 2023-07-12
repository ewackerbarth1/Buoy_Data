# Buoy Utilities

import numpy as np
import requests
from bs4 import BeautifulSoup

def parseBOIFile(boiFName: str) -> list:
    with open(boiFName) as f:
        stationIDs = f.readlines()
        boiList = [s.strip() for s in stationIDs]

    print('buoys of interest:')
    print(boiList)
    return boiList

def getActiveNDBCStations() -> dict:
    # get and parse the active stations webpage
    activeStationsUrl = 'https://www.ndbc.noaa.gov/activestations.xml'
    ndbcPage = requests.get(activeStationsUrl)       #<class 'requests.models.Response'>
    buoySoup = BeautifulSoup(ndbcPage.content, 'xml') #<class 'bs4.BeautifulSoup'>
    
    # find buoy station types
    buoyStations = buoySoup.find_all("station") #, {"type": "buoy"})
    print('# of active buoys = ' + str(len(buoyStations))) # 347 active buoys as of 1/31/2021
    
    # build buoy dictionary with id as key and (lat, lon) as value
    activeBuoys = dict()
    for buoy in buoyStations:
        buoyID = buoy.get("id")
        buoyLon = buoy.get("lon")
        buoyLat = buoy.get("lat")
        activeBuoys[buoyID] = (float(buoyLat), float(buoyLon))

    return activeBuoys

def getActiveBOI(boiFName: str) -> dict:
    boiList = parseBOIFile(boiFName)
    activeNDBCStations = getActiveNDBCStations()
    activeBOI = dict()
    for boi in boiList:
        if boi not in activeNDBCStations:
            print(f'station {boi} either does not exist or is not active!')
        else:
            activeBOI[boi] = activeNDBCStations[boi]

    return activeBOI

def makeCircularHist(ax, x, bins=16, density=True, offset=0, gaps=True):
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
                     edgecolor='C0', fill=False, linewidth=1)

    # Set the direction of the zero angle
    ax.set_theta_offset(offset)

    # Remove ylabels for area plots (they are mostly obstructive)
    if density:
        ax.set_yticks([])

    return n, bins, patches

def calculateBearingAngle(p1: tuple[float], p2: tuple[float]) -> float:
    lat1, lon1 = p1
    lat2, lon2 = p2

    lat1, lon1 = lat1 * np.pi / 180, lon1 * np.pi / 180
    lat2, lon2 = lat2 * np.pi / 180, lon2 * np.pi / 180

    dLon = lon2 - lon1

    y = np.sin(dLon) * np.cos(lat2)
    x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dLon)

    brng = np.arctan2(y, x)
    brng = (brng * 180 / np.pi + 360) % 360
    return brng

