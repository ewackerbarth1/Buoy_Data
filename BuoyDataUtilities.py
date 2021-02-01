# Buoy Utilities

import requests
from bs4 import BeautifulSoup
import pandas as pd


def constructBuoyDict():
    '''
    Returns a NDBC buoy dictionary where the station IDs form the keys and the
    corresponding (lat, lon) tuples form the values

    Inputs:

    Outputs:
        buoysDict (dict): key = station ID, value = (lat, lon)
    '''

    # get and parse the active stations webpage
    activeStationsUrl = 'https://www.ndbc.noaa.gov/activestations.xml'
    ndbcPage = requests.get(activeStationsUrl)       #<class 'requests.models.Response'>
    buoySoup = BeautifulSoup(ndbcPage.content, 'xml') #<class 'bs4.BeautifulSoup'>

    # find buoy station types
    buoyStations = buoySoup.find_all("station", {"type": "buoy"})
    print('# of active buoys = ' + str(len(buoyStations))) # 347 active buoys as of 1/31/2021

    # build buoy dictionary with id as key and (lat, lon) as value
    buoysDict = dict()
    for buoy in buoyStations:
        thisKey = buoy.get("id")
        thisLon = buoy.get("lon")
        thisLat = buoy.get("lat")
        buoysDict[thisKey] = (float(thisLat), float(thisLon))

    return buoysDict


def findNearbyBuoys(buoysDict, lat, lon, dLat, dLon):
    '''
    Trims the dictionary of active buoys based on the provided region of
    interest.

    Inputs:
        buoysDict (dict): keys are station IDs and values are (lat, lon) tuples
        lat (int/float): latitude
        lon (int/float): longitude
        dLat (int/float): half of latitude extent
        dLon (int/float): half of longitude extent

    Outputs:
        nearbyBuoys (dict): only includes buoys in [lat-dLat, lat+dLat] and
                          [lon-dLon, lon+dLon]
    '''

    # check for invalid inputs
    if lat < -90 or lat > 90:
        print('latitude must be > -90 and < 90 degrees')
        return

    if lon < -180 or lon > 180:
        print('longitude must be > -180 and < 180 degrees')
        return

    if dLat < 0 or dLat > 90:
        print('dLatitude must be > 0 and < 90 degrees')
        return

    if dLon < 0 or dLon > 180:
        print('dLongitude must be > 0 and < 180 degrees')
        return

    # remove buoys that are not within the region of interest
    nearbyBuoys = dict()
    for key in buoysDict:
        latLonTup = buoysDict[key]
        # check latitude (-90, 90 deg)
        latCheck = intervalCheck(lat, dLat, latLonTup[0], 90)

        # check longitude (-180, 180 deg)
        lonCheck = intervalCheck(lon, dLon, latLonTup[1], 180)
        if latCheck and lonCheck:
            nearbyBuoys[key] = latLonTup

    print('# of buoys in region of interest = ' + str(len(nearbyBuoys)))
    return nearbyBuoys


def intervalCheck(x, dx, x0, halfRange):
    '''
    Returns True if x0 is within the interval [x-dx, x+dx], otherwise returns
    false.

    Inputs:
        x (int/float): center of interval
        dx (int/float): 1/2 of the extent of the interval
        x0 (int/float): test point
        halfRange (int/float):

    Outputs:
        boolean: True if x0 is within interval, false if not
    '''

    xMax = x + dx
    xMin = x - dx

    if x0 <= xMax and x0 >= xMin:
        return True
    else:
        if xMax > halfRange: # interval of interest wraps around in + direction
            if x0 < (xMax - 2*halfRange) and x0 > (xMin - 2*halfRange):
                return True
            else:
                return False

        elif xMin < -halfRange: # interval of interest wraps around in - direction
            if x0 < (xMax + 2*halfRange) and x0 > (xMin + 2*halfRange):
                return True
            else:
                return False
        else:
            return False


def buoysDictToDF(buoysDict):
    '''
    Constructs a buoy data frame given the dictionary input

    Inputs:
        buoysDict (dict): dictionary with key = 'ID', value = (lat, lon)

    Outputs:
        buoysDF (DataFrame): data frame with 3 columns, 1) ID, 2) lat, 3) lon
    '''

    buoysDF = pd.DataFrame(buoysDict.items(), columns=['ID', 'latlon'])
    #print(buoysDF)
    buoysDF[['lat', 'lon']] = pd.DataFrame(buoysDF['latlon'].tolist())
    buoysDF.pop('latlon')
    #print(buoysDF)

    return buoysDF
