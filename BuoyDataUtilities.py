# Buoy Utilities

import requests
from bs4 import BeautifulSoup


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
        buoysDict[thisKey] = (thisLat, thisLon)


    return buoysDict
