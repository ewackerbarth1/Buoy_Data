import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import argparse
import re
import warnings
import time
from datetime import date
from BuoyDataUtilities import cleanBuoyData, buildSwellDirDict, makeCircularHist, constructBuoyDict
import config
import pymysql

def formatPandasDateTimeForMySQL(pdDateTime):
    mySQLDateTime = pdDateTime.strftime('%Y-%m-%d %H:%M:%S')
    return mySQLDateTime

def convertDegreesToRadians(thetaDeg: float) -> float:
    return thetaDeg * np.pi / 180

def calcDistances(latLon1: tuple, latLon2: tuple) -> float:
    lat1Rad, lon1Rad = convertDegreesToRadians(latLon1[0]), convertDegreesToRadians(latLon1[1])
    lat2Rad, lon2Rad = convertDegreesToRadians(latLon2[0]), convertDegreesToRadians(latLon2[1])

    dLat = lat2Rad - lat1Rad
    dLon = lon2Rad - lon1Rad

    a = np.sin(dLat / 2) * np.sin(dLat / 2) + np.cos(lat1Rad) * np.cos(lat2Rad) * np.sin(dLon / 2) * np.sin(dLon / 2)

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    earthRadius = 6371e3   # meters
    distMeters = earthRadius * c

    metersPerNMi = 1852
    distNMi = distMeters / metersPerNMi# nautical miles
    return distNMi


class BuoySelector():
    def __init__(self, currentLoc: tuple, boiFName: str):
        self.currentLoc = currentLoc
        self.boiFName = boiFName

        #self.getActiveBuoys()
        #self.getBuoysOfInterest()
        #self.activeBuoys
        #self.activeBOI

    def getActiveBuoys(self):
        self.activeBuoys = constructBuoyDict()

    def parseBOIFile(self) -> list:
        with open(self.boiFName) as f:
            stationIDs = f.readlines()
            boiList = [s.strip() for s in stationIDs]

        print('buoys of interest:')
        print(boiList)
        return boiList

    def getActiveBOI(self, attemptedBOI):
        self.activeBOI = dict()
        for boi in attemptedBOI:
            if boi not in self.activeBuoys:
                print(f'station {boi} either does not exist or is not active!')
            else:
                self.activeBOI[boi] = self.activeBuoys[boi]

    def getBuoysOfInterest(self):
        boiList = self.parseBOIFile()
        self.getActiveBOI(boiList)

    def initializeBOIDF(self):

        boiData = []
        for stationID, latLon in self.activeBOI.items():
            distanceAway = calcDistances(self.currentLoc, latLon)
            hoverText = f'{stationID}, {distanceAway:0.2f} NM away'
            thisBuoyData = [stationID, latLon[0], latLon[1], distanceAway, hoverText]
            boiData.append(thisBuoyData)

        self.buoysDF = pd.DataFrame(boiData, columns=['ID', 'lat', 'lon', 'distanceAway', 'hoverText'])
        print('Buoys dataframe:')
        print(self.buoysDF)

    def mapBuoys(self):
        fig = go.Figure(go.Scattergeo())
        fig.update_geos(projection_type="natural earth",
                showcoastlines = True,
                showland = True,
                showocean = True,
                showlakes = True,
                resolution = 50, 
                center = dict(
                    lon = self.currentLoc[1], 
                    lat = self.currentLoc[0]
                    )
                )

        fig.add_trace(go.Scattergeo(lon = [self.currentLoc[1]], lat = [self.currentLoc[0]],
            mode = 'markers',
            name = 'Current Location',
            marker = dict(
                color = 'rgb(0, 0, 255)',
                symbol = 'x'
                )
            ))

        fig.add_trace(go.Scattergeo(
            lon = self.buoysDF['lon'],
            lat = self.buoysDF['lat'],
            text = self.buoysDF['hoverText'],
            mode = 'markers',
            name = 'buoys',
            marker = dict(
                color = 'rgb(255, 0, 0)'
                )
            )
            )

        fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})
        fig.show()
    

class NDBCBuoy():
    def __init__(self, stationID):
        self.stationID = stationID
        self.baseURLRealtime = 'https://www.ndbc.noaa.gov/data/realtime2/'
        self.swellDict = buildSwellDirDict()
        self.buildStationURLs()
        #self.baseURLHistorical = 
        #self.urlRealtime
        #self.urlHistorical
        #self.dataFrameRealtime
        #self.dataFrameHistorical
        #self.lat
        #self.lon
        #self.nSampsPerHour

    def buildStationURLs(self):
        self.urlRealtime = f'{self.baseURLRealtime}{self.stationID}.spec'

    def makeHistoricalDataRequest(self, year: int):
        historicalURL = f'https://www.ndbc.noaa.gov/view_text_file.php?filename={self.stationID}h{year}.txt.gz&dir=data/historical/stdmet/'
        nSecondsToPause = 5
        print(f'requesting {historicalURL} after {nSecondsToPause}s pause...')
        time.sleep(nSecondsToPause)
        ndbcPage = requests.get(historicalURL)       #<class 'requests.models.Response'>
        return ndbcPage

    def makeRealtimeDataRequest(self):
        nSecondsToPause = 5
        print(f'requesting {self.urlRealtime} after {nSecondsToPause}s pause...')
        time.sleep(nSecondsToPause)
        ndbcPage = requests.get(self.urlRealtime)       #<class 'requests.models.Response'>
        return ndbcPage

    def parseRealtimeData(self, ndbcPage):
        #TODO: check other ways of doing this!!
        buoySoup = BeautifulSoup(ndbcPage.content, 'html.parser') #<class 'bs4.BeautifulSoup'>

        soupString = str(buoySoup)# convert soup to a string
        rowList = re.split("\n+", soupString)# split string based on row divisions
        rowList = rowList[:-1]# TODO: remove last entry if necessary
        entryList = [re.split(" +", iRow) for iRow in rowList]# split each row into a list of individual entries using spaces, so we have a list of lists
    
        # build data frame
        buoyDF = pd.DataFrame(entryList[2:], columns = entryList[0])  # ignore first 2 rows
        return buoyDF

    def checkSamplingPeriod(self, buoyDF):
        nSamplesToCheck = 10
        dateSeries = buoyDF['Date']
        dateSeries = dateSeries[:nSamplesToCheck]
        expectedInterval = pd.Timedelta(1, unit='hours')
        self.nSampsPerHour = 1

        for iSample in range(nSamplesToCheck-1):
            thisInterval = dateSeries[iSample] - dateSeries[iSample+1]
            if thisInterval != expectedInterval:
                self.nSampsPerHour = round(expectedInterval.value / thisInterval.value)
                warnings.warn(f'Detected sampling period of {thisInterval} instead of {expectedInterval} for this buoy! Setting self.nSamperPerHour to {self.nSampsPerHour}')


    def cleanRealtimeDataFrame(self, buoyDF):
        buoyDF['Date'] = buoyDF['#YY'] + buoyDF['MM'] + buoyDF['DD'] + buoyDF['hh'] + buoyDF['mm']# add a date column
        buoyDF['Date'] = pd.to_datetime(buoyDF['Date'], format='%Y%m%d%H%M')

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
        buoyDF["SwD"] = buoyDF["SwD"].map(self.swellDict)
        #print(buoyDF)
        
        # do we need a call to pd.to_numeric for the swell direction
        buoyDF["SwD"] = pd.to_numeric(buoyDF["SwD"])
        return buoyDF

    def buildRealtimeDataFrame(self):
        ndbcPage = self.makeRealtimeDataRequest()
        rawDF = self.parseRealtimeData(ndbcPage)
        self.dataFrameRealtime = self.cleanRealtimeDataFrame(rawDF)
        self.checkSamplingPeriod(self.dataFrameRealtime)

    def getHistoricalYearsAndMonths(self, nYears: int):
        todaysDate = date.today()
        currentYear, currentMonth = todaysDate.year, todaysDate.month
        monthsList = []
        # need to get data from prior month, this month, next month
        for dMonth in range(-1, 2):
            monthsList.append((currentMonth + dMonth) % 12)

        yearsList = []
        for dYear in range(1, nYears+1):
            yearsList.append(currentYear - dYear)

        return yearsList, monthsList

    def parseHistoricalData(self, ndbcPage, monthsToCheck):
        buoySoup = BeautifulSoup(ndbcPage.content, 'html.parser') #<class 'bs4.BeautifulSoup'>

        soupString = str(buoySoup)# convert soup to a string
        rowList = re.split("\n+", soupString)# split string based on row divisions
        rowList = rowList[:-1]# TODO: remove last entry if necessary
        entryList = [re.split(" +", iRow.strip()) for iRow in rowList]# split each row into a list of individual entries using spaces, so we have a list of lists
    
        # build data frame
        buoyDF = pd.DataFrame(entryList[2:], columns = entryList[0])  # ignore first 2 rows
        print(f'initial historical buoy df:')
        print(buoyDF)

        # remove every element that doesn't have waveheight data
        rowsToRemove = buoyDF.loc[buoyDF['WVHT'] == '99.00']
        #print(f'# of rows to remove = {len(rowsToRemove)}')
        #print(f'rows to remove = {rowsToRemove}')
        buoyDF = buoyDF.drop(rowsToRemove.index)
        #print(f'Parsed data frame:')
        #print(buoyDF)

        # remove elements not in correct months
        monthsToCheckStrs = []
        for thisMonth in monthsToCheck:
            monthStr = str(thisMonth)
            if thisMonth < 10:
                monthStr = '0' + monthStr 
            monthsToCheckStrs.append(monthStr)

        buoyDF = buoyDF[buoyDF['MM'].isin(monthsToCheckStrs)]
        print('final parsed historical df:')
        print(buoyDF)
        return buoyDF

    def cleanHistoricalDataFrame(self, buoyDF):
        buoyDF["WVHT"] = pd.to_numeric(buoyDF["WVHT"])
        return buoyDF


    def buildHistoricalDataFrame(self, nYears: int):
        yearsToCheck, monthsToCheck = self.getHistoricalYearsAndMonths(nYears)
        print(f'Grabbing historical data from years of {yearsToCheck} and months {monthsToCheck}')
        print(f'To limit requests to NDBC webpage, collecting {len(yearsToCheck)} years of historical data will take us about {len(yearsToCheck)*5}s')
        historicalDataFrames = []
        for yearToCheck in yearsToCheck:
            ndbcPage = self.makeHistoricalDataRequest(yearToCheck)
            rawDF = self.parseHistoricalData(ndbcPage, monthsToCheck)
            thisDataFrame = self.cleanHistoricalDataFrame(rawDF)
            # make any additionalChecks
            historicalDataFrames.append(thisDataFrame)

        self.dataFrameHistorical = pd.concat(historicalDataFrames)

    def analyzeWVHTDistribution(self, dataSetName):
        nSamplesToAvg = 3   # most recent n samples to check
        waveheightsRT = self.dataFrameRealtime['WVHT']
        print(f'Last {nSamplesToAvg} samples: {waveheightsRT[0:nSamplesToAvg]}')
        recentAvg = waveheightsRT[0:nSamplesToAvg].mean()
        print(f'mean = {recentAvg}')

        if dataSetName == 'historical':
            waveheightsSorted = self.dataFrameHistorical['WVHT'].sort_values().to_numpy() # ascending
        elif dataSetName == 'realtime':
            waveheightsSorted = self.dataFrameRealtime['WVHT'][nSamplesToAvg+1:].sort_values().to_numpy() # ascending
        else:
            raise ValueError('historical and realtime are the only supported data sets')

        print(f'sorted {dataSetName} wvhts: {waveheightsSorted}')

        nTotalValues = len(waveheightsSorted)
        ptr = 0
        while ptr < nTotalValues and recentAvg > waveheightsSorted[ptr]:
            ptr += 1

        greaterThanFrac = ptr / nTotalValues 
        print(f'current swell is greater than {greaterThanFrac * 100 :0.2f}% of {dataSetName} data')

    def plotPastNDaysWvht(self, nDays: int):
        if nDays > 45:
            print(f'Only have 45 days worth of realtime data so just plotting the last 45 days')
            nDays = 45
        nSamples = 24 * self.nSampsPerHour * nDays   # 1 sample per hour

        # TODO: wrap into function
        waveheights = self.dataFrameRealtime['WVHT']
        sampleDates = self.dataFrameRealtime['Date']
        waveheights = waveheights[:nSamples]
        sampleDates = sampleDates[:nSamples]
        waveheights = waveheights[::-1]  # reverse so that the most recent sample is the last array value
        sampleDates = sampleDates[::-1]

        plt.plot(sampleDates, waveheights, 'o-')
        plt.xlabel('Sample times')
        plt.ylabel('Wave height [m]')
        plt.title(f'{nDays}-day trailing window of wave heights for station {self.stationID}')
        plt.grid()
        plt.gca().tick_params(axis='x', labelrotation=45)
        plt.show()

    def plotWvhtDistribution(self):
        nSamplesToLayerOn = 3   # most recent n samples to plot
        waveheightsRT = self.dataFrameRealtime['WVHT']
        waveheightsHistorical = self.dataFrameHistorical['WVHT']
        plt.hist(waveheightsHistorical, density=True)
        plt.plot(waveheightsRT[0:nSamplesToLayerOn], np.full_like(waveheightsRT[0:nSamplesToLayerOn], -0.05), '|k', markeredgewidth=1)
        plt.grid()
        plt.xlabel('Wave heights [m]')
        plt.ylabel('density')
        plt.title(f'Wave heights pmf for station {self.stationID}')
        plt.show()

    def plotWvhtAndPeriodJointDistribution(self):
        nSamplesToLayerOn = 3   # most recent n samples to plot
        waveheights = self.dataFrameRealtime['WVHT']
        swellPeriods = self.dataFrameRealtime['SwP']
        plt.hist2d(waveheights, swellPeriods, density=True)
        plt.plot(waveheights[0:nSamplesToLayerOn], swellPeriods[0:nSamplesToLayerOn], 'wo')
        plt.grid()
        plt.xlabel('Wave heights [m]')
        plt.ylabel('Swell periods [s]')
        plt.title(f'wvht and swp joint pmf for station {self.stationID}')
        plt.show()

    def plotSwellDirectionDistribution(self):
        nSamplesToLayerOn = 3   # most recent n samples to plot
        swellDirections = self.dataFrameRealtime['SwD']
        swellDirectionsRadians = swellDirections * (np.pi / 180)

        # Visualise by area of bins
        fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
        makeCircularHist(ax, swellDirectionsRadians)
        ax.plot(swellDirections[0:nSamplesToLayerOn], np.full_like(swellDirections[0:nSamplesToLayerOn], 0.2), 'ok', markeredgewidth=1)
        ax.set_title(f'Swell direction distribution for station {self.stationID}')
        ax.grid(True)
        ax.set_xticklabels(['N', 'NW', 'W', 'SW', 'S', 'SE', 'E', 'NE'])   #TODO: this produces a warning!!
        plt.show()

    def getMostRecentReading():
        print()
        return []

class DatabaseInteractor():
    #TODO: the config is just for the database so maybe find a way to localize the import instead of a global one at the top of this file
    def __init__(self):
        self.establishConnection()
        #self.successfulConnection

    def establishConnection(self):
        try:
            self.connection = pymysql.connect(host=config.ENDPOINT,
                    port=config.PORT,
                    user=config.USERNAME,
                    password=config.PASSWORD,
                    database=config.DBNAME,
                    cursorclass=pymysql.cursors.Cursor,
                    ssl_ca=config.SSL_CA
                    )

            print('Successful RDS connection!')
            self.successfulConnection = True

        except Exception as e:
            print(f'RDS connection failed: {e}')
            self.connection = None
            self.successfulConnection = False

    def checkForBuoyExistenceInDB(self, stationID: str) -> bool:
        # TODO: The count is either going to be 1 or 0, so there is definitely a more precise SQL command
        # query stations table for stationID entry
        thisCursor = self.connection.cursor()
        thisCursor.execute('SELECT COUNT(*) FROM stations where id = %s', (stationID,))

        idCount = thisCursor.fetchone()[0]
        thisCursor.close()

        if idCount > 0:
            return True
        else:
            return False

    def addBuoyToStationsTable(self, stationID: str, stationLatLon: tuple):
        thisCursor = self.connection.cursor()
        thisCursor.execute('INSERT INTO stations (id, location) VALUES (%s, POINT(%s, %s))', (stationID, stationLatLon[0], stationLatLon[1]))
        thisCursor.close()
        self.connection.commit()

    def getAllDataFromStationsTable(self):
        thisCursor = self.connection.cursor()
        thisCursor.execute('SELECT id, ST_X(location) as latitude, ST_Y(location) as longitude FROM stations')
        allRows = thisCursor.fetchall()
        thisCursor.close()
        return allRows

    def printContentsOfStationsTable(self):
        allRows = self.getAllDataFromStationsTable()
        print(f'stations table = {allRows}')

    def removeRealtimeSamplesForStation(self, stationID):
        thisCursor = self.connection.cursor()
        thisCursor.execute('DELETE FROM realtime_data WHERE station_id = %s', (stationID,))
        thisCursor.close()

    def addRealtimeSamplesForStation(self, stationID, buoyRealtimeDataframe):
        thisCursor = self.connection.cursor()
        for iRow in range(len(buoyRealtimeDataframe)):
            wvht = buoyRealtimeDataframe.iloc[iRow]['WVHT']
            swp = buoyRealtimeDataframe.iloc[iRow]['SwP']
            swdir = buoyRealtimeDataframe.iloc[iRow]['SwD']
            dateTime = formatPandasDateTimeForMySQL(buoyRealtimeDataframe.iloc[iRow]['Date'])
            thisCursor.execute('INSERT INTO realtime_data (station_id, timestamp, wvht, swp, swdir) VALUES (%s, %s, %s, %s, %s)', (stationID, dateTime, wvht, swp, swdir))

        thisCursor.close()

    def updateRealtimeDataEntry(self, stationID, buoyRTDF):
        print(f'Removing realtime data for station {stationID}')
        startTime = time.time()
        self.removeRealtimeSamplesForStation(stationID)
        print(f'Removing realtime data took {time.time() - startTime} s')

        print(f'Adding realtime data for station {stationID}')
        startTime = time.time()
        self.addRealtimeSamplesForStation(stationID, buoyRTDF)
        print(f'Adding realtime data took {time.time() - startTime} s')

        self.connection.commit()
        print(f'Updated realtime data for station {stationID}')

    def closeConnection(self):
        self.connection.close()

def updateRealtimeData(args):
    # need a list of buoys
    desiredLocation = (args.lat, args.lon)
    myBuoySelector = BuoySelector(desiredLocation, args.bf)
    boiList = myBuoySelector.parseBOIFile()

    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        print('Could not update data because of unsuccessful connection')
        return

    for stationID in boiList:
        # check if buoy is in stations table
        buoyInTable = dbInteractor.checkForBuoyExistenceInDB(stationID)
        if not buoyInTable:
            print(f'station {stationID} is not in the database, so please add it before attempting to update its data!')
            continue

        # if it is, then get realtime data set for it 
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.buildRealtimeDataFrame()

        # add realtime data set to realtime_data table
        dbInteractor.updateRealtimeDataEntry(stationID, thisBuoy.dataFrameRealtime)

    dbInteractor.closeConnection()

def addDesiredBuoysToDB(args):
    desiredLocation = (args.lat, args.lon)
    myBuoySelector = BuoySelector(desiredLocation, args.bf)

    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        print('Could not add buoys because of unsuccessful connection')
        return

    for stationID, latLon in myBuoySelector.activeBOI.items():
        buoyInTable = dbInteractor.checkForBuoyExistenceInDB(stationID)
        if buoyInTable:
            print(f'station {stationID} is already in the database!')
        else:
            print(f'adding station {stationID} to database...')
            dbInteractor.addBuoyToStationsTable(stationID, latLon)

    dbInteractor.printContentsOfStationsTable()
    dbInteractor.closeConnection()

def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument("-s", type=str, required=True, help="buoy station id")
    #parser.add_argument("-N", type=int, required=True, help="# of years for historical data")
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    #parser.add_argument("--action", type=str, required=True, help="update-realtime, update-historical, or display-data")
    args = parser.parse_args()

    updateRealtimeData(args)
    #addDesiredBuoysToDB(args)
    #desiredLocation = (args.lat, args.lon)

    #if args.action == 'update-realtime':
    #    updateRealtimeData(args)
    #elif args.action == 'update-historical':
    #    asdf
    #elif args.action == 'display-data':

    #else:
    #    ValueError('Invalid input for action argument! Valid inputs are: update-realtime, update-historical, display-data')


    #myBuoySelector = BuoySelector(desiredLocation, args.bf)
    #myBuoySelector.initializeBOIDF()
    #myBuoySelector.mapBuoys()
    
    #buoysDF = initializeNearbyBuoyDF(desiredLocation)
    #mapBuoys(buoysDF, desiredLocation)

    #buoy1 = NDBCBuoy(args.s)
    #buoy1.buildRealtimeDataFrame()
    #buoy1.buildHistoricalDataFrame(args.N)
    ##buoy1.plotPastNDaysWvht(10)
    #buoy1.analyzeWVHTDistribution('realtime')
    #buoy1.analyzeWVHTDistribution('historical')
    #buoy1.plotWvhtDistribution()
    ##buoy1.plotWvhtAndPeriodJointDistribution()
    ##buoy1.plotSwellDirectionDistribution()

if __name__ == "__main__":
    main()
