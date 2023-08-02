# Buoy Utilities

import numpy as np
import requests
from bs4 import BeautifulSoup
import pandas as pd

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

def convertMetersToNM(d: float) -> float:
    metersPerNM = 1852
    return d / metersPerNM

def convertDegreesToRadians(thetaDeg: float) -> float:
    return thetaDeg * np.pi / 180

def convertSwellETAToDistance(swPSeconds: float, etaHours: float) -> float:
    swellSpeedNMPerHour = 1.5 * swPSeconds  # NM / hour
    distanceAway = swellSpeedNMPerHour * etaHours # NM
    return distanceAway

def convertDistanceToSwellETA(swPSeconds: float, stationDistNM: float) -> float:
    swellSpeedNMPerHour = 1.5 * swPSeconds  # NM / hour
    etaHours = stationDistNM / swellSpeedNMPerHour # hours
    return etaHours 

def calcDistanceBetweenNM(latLon1: tuple, latLon2: tuple) -> float:
    lat1Rad, lon1Rad = convertDegreesToRadians(latLon1[0]), convertDegreesToRadians(latLon1[1])
    lat2Rad, lon2Rad = convertDegreesToRadians(latLon2[0]), convertDegreesToRadians(latLon2[1])

    dLat = lat2Rad - lat1Rad
    dLon = lon2Rad - lon1Rad

    a = np.sin(dLat / 2) * np.sin(dLat / 2) + np.cos(lat1Rad) * np.cos(lat2Rad) * np.sin(dLon / 2) * np.sin(dLon / 2)

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    earthRadius = 6371e3   # meters
    distMeters = earthRadius * c

    #metersPerNMi = 1852
    #distNMi = distMeters / metersPerNMi# nautical miles
    distNM = convertMetersToNM(distMeters)
    return distNM

def estimateDensityGaussianKernel(data: np.ndarray[np.float64]) -> tuple:
    xd = np.linspace(0, max(data), 100)
    density = sum(norm(xi).pdf(xd) for xi in data)
    density = density / (sum(density) * (xd[1]-xd[0]))
    return xd, density

def estimateDensityTophatKernel(data: np.ndarray[np.float64], binWidth: float) -> tuple:
    xd = np.linspace(0, max(data), 100)
    density = np.zeros(xd.shape)
    for xi in data:
        densityIdxs = abs(xi - xd) < 0.5*binWidth
        density[densityIdxs] += 1

    density = density / (sum(density) * (xd[1] - xd[0]))
    return xd, density

def getNthPercentileSample(samplingVector: np.ndarray[np.float64], pmf: np.ndarray[np.float64], nthPercentile: float) -> np.float64:
    mass = 0
    sampleIdx = 0
    samplingBinWidth = samplingVector[1] - samplingVector[0]
    while mass < nthPercentile / 100 and sampleIdx < len(samplingVector):
        mass += pmf[sampleIdx] * samplingBinWidth
        sampleIdx += 1

    return samplingVector[sampleIdx]

def getNthPercentileSampleWithoutPMF(wvhts: np.ndarray, nthPercentile: int) -> np.float64:
    nSamples = len(wvhts)
    ithSample = int(np.ceil(nthPercentile / 100 * nSamples) - 1)
    sortedWvhts = np.sort(wvhts)
    return sortedWvhts[ithSample]

def getMonthlyDF(df: pd.core.frame.DataFrame, month: int) -> pd.core.frame.DataFrame:
    return df[df['Date'].dt.month == month]

def getMonthName(month: int) -> str:
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return months[month-1]

def truncateAndReverse(dataSeries: np.ndarray, nSamples: int) -> np.ndarray:
    truncated = dataSeries[:nSamples]
    return truncated[::-1]

def restricted_int(x):
    x = int(x)
    if x < 1 or x > 44:
        raise argparse.ArgumentTypeError(f"Value must be an integer between 1 and 44. Got {x}")

    return x
