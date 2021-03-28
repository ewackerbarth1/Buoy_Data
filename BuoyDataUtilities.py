# Buoy Utilities

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import numpy as np
import traceback


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

    Inputs (buoysDict):
        buoysDict (dict): dictionary with key = 'ID', value = (lat, lon)

    Outputs [buoysDF]:
        buoysDF (DataFrame): data frame with 3 columns, 1) ID, 2) lat, 3) lon
    '''

    buoysDF = pd.DataFrame(buoysDict.items(), columns=['ID', 'latlon'])
    #print(buoysDF)
    buoysDF[['lat', 'lon']] = pd.DataFrame(buoysDF['latlon'].tolist())
    buoysDF.pop('latlon')
    #print(buoysDF)

    return buoysDF


def collectBuoyData(nearbyBuoysDict):
    '''
    Collects buoy data from nearby buoys

    Inputs (nearbyBuoysDict):
        nearbyBuoysDict (dict): dictionary with key = 'ID', value = (lat, lon)

    Outputs [allBuoysDA]:
        allBuoysDA (np.ndArray): 3D array which is samples x data type x buoy
    '''
    
    buoyCounter = 0

    # consider data from past 45 days
    baseURL = 'https://www.ndbc.noaa.gov/data/realtime2/'

    for key in nearbyBuoysDict:

        print('Requesting data from buoy #', key)

        # build buoy data URL
        buoyURL = baseURL + key + '.spec'

        # connect to and parse the webpage
        ndbcPage = requests.get(buoyURL)       #<class 'requests.models.Response'>
        buoySoup = BeautifulSoup(ndbcPage.content, 'html.parser') #<class 'bs4.BeautifulSoup'>

        # get relevant data in data frame
        try:
            thisBuoyDataFrame = getBuoyDataFrame(buoySoup)
        except Exception: 
            print('Unable to successfully request data from buoy #', key)
            traceback.print_exc()
            time.sleep(5)
            continue

        # split into pd.Series with date/time and 2D numpy array with relevant swell data
        thisBuoyDataFrame.drop(['Date'], inplace=True, axis=1)
        #print(thisBuoyDataFrame.to_string())
        thisBuoyDA = thisBuoyDataFrame.to_numpy()

        if buoyCounter == 0:
            allBuoysDA = thisBuoyDA 
        elif buoyCounter == 1:
            # check size
            thisBuoyDA = checkArrayShape(thisBuoyDA, allBuoysDA)

            # 
            allBuoysDA = np.concatenate((allBuoysDA[:, :, np.newaxis], thisBuoyDA[:, :, np.newaxis]), axis=2)

        else:
            # check size
            thisBuoyDA = checkArrayShape(thisBuoyDA, allBuoysDA)
            
            # 
            allBuoysDA = np.concatenate((allBuoysDA, thisBuoyDA[:, :, np.newaxis]), axis=2)
        
        buoyCounter = buoyCounter + 1

        # pause to limit number of requests per second
        time.sleep(5)

    return allBuoysDA


def getBuoyDataFrame(webpageBS):
    '''
    Collects time series data and returns data frame

    Inputs (webpageBS):
        webpageBS (bs4): webpage contents as beautiful soup object

    Outputs [buoyDF]:
        buoyDF (DataFrame): data frame with desired data
    '''

    # convert soup to a string
    soupString = str(webpageBS)

    # split string based on row divisions
    rowList = re.split("\n+", soupString)

    # @2do: remove last entry if necessary
    rowList = rowList[:-1]

    # split rows into individual entries using spaces
    entryList = [re.split(" +", iRow) for iRow in rowList]

    # build data frame
    buoyDF = pd.DataFrame(entryList[2:], columns = entryList[0])  # ignore first 2 rows

    # add a date column
    buoyDF['Date'] = buoyDF['#YY'] + buoyDF['MM'] + buoyDF['DD'] + buoyDF['hh'] + buoyDF['mm']

    # drop unncessary columns
    to_drop = ['#YY', 'MM', 'DD', 'hh', 'mm', 'STEEPNESS', 'SwH', 'WWH', 'WWP', 'WWD', 'APD', 'MWD']
    buoyDF.drop(to_drop, inplace=True, axis=1)

    # clean data
    buoyDF = buoyDF.applymap(cleanBuoyData)
    print(buoyDF)

    # change type of swell size and period data
    buoyDF["WVHT"] = pd.to_numeric(buoyDF["WVHT"])
    buoyDF["SwP"] = pd.to_numeric(buoyDF["SwP"])

    # convert swell direction to degrees
    swellDict = buildSwellDirDict()
    buoyDF["SwD"] = buoyDF["SwD"].map(swellDict)
    #print(buoyDF)
    
    # do we need a call to pd.to_numeric for the swell direction
    buoyDF["SwD"] = pd.to_numeric(buoyDF["SwD"])

    return buoyDF


def cleanBuoyData(dfItem):
    '''
    Cleans the buoy data by removing the "MM" characterization of missing data

    Inputs (dfItem):
        dfItem (): element of Pandas data frame

    Outputs [dfItem]:
        dfItem (): input value or "0" depending on whether data exists
    '''

    if dfItem == "MM":
        return "0.0"
    else:
        return dfItem

def buildSwellDirDict():
    '''
    Builds dictionary to convert swell direction strings to degrees
    N --> 0
    W --> 90
    S --> 180
    E --> 270

    Inputs :

    Outputs [swellDirDict]:
        swellDirDict (dict): swell direction dictionary

    '''

    # build dictionary
    swellDirDict = dict()
    dirStrings = ['N', 'NNW', 'NW', 'WNW',
                  'W', 'WSW', 'SW', 'SSW',
                  'S', 'SSE', 'SE', 'ESE',
                  'E', 'ENE', 'NE', 'NNE']
    dirDegrees = np.arange(0, 382.5, 22.5)  # 0:22.5:360
    iCount = 0
    for iDir in dirStrings:
        swellDirDict[iDir] = dirDegrees[iCount]
        iCount = iCount + 1

    return swellDirDict


def checkArrayShape(a, b):
    '''
    Checks whether the size of array a matches the size of array b along the first dimension

    Inputs (a, b):
        a (np.ndarray): 2D, m x n array
        b (np.ndarray): ND, j x n x ... array

    Outputs [a]:
        a (np.ndarray): 2D, j x n array

    '''
    # check size
    nARows = a.shape[0]
    nBRows = b.shape[0]

    if nARows > nBRows:
        print('Truncating data array, # A rows = ', nARows, ' # B rows = ', nBRows)
        a = a[:nBRows]

    elif nARows < nBRows:
        print('Appending zeros to data array, # A rows = ', nARows, ' # B rows = ', nBRows)
        nCol = a.shape[1]
        nExtraRows = nBRows - nARows
        a = np.concatenate((a, np.zeros((nExtraRows, nCol))), axis=0)

    return a



