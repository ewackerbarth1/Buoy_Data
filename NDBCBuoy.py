import requests
from bs4 import BeautifulSoup
from scipy.stats import norm
import numpy as np
import pandas as pd
import re
import time
from datetime import date, datetime, timedelta
from DatabaseInteractor import DatabaseInteractor


def cleanBuoyData(dfItem):
    if dfItem == "MM":
        return "0.0"
    else:
        return dfItem


class NDBCBuoy():
    def __init__(self, stationID: str):
        self.stationID = stationID
        self.baseURLRealtime = 'https://www.ndbc.noaa.gov/data/realtime2/'
        self.swellDict = self.buildSwellDirDict()
        self.urlRealtime = self.buildStationURLs()
        self.nYearsBack = 5   # number of years to go back for historical analysis
        self.nHistoricalMonths = 3 # number of months in historical data range
        self.nSecondsToPauseBtwnRequests = 5

        # default values
        self.nSampsPerHour = -1
        self.dataFrameRealtime = []
        self.dataFrameHistorical = []
        self.lat = 0.0
        self.lon = 0.0
        self.recentWVHT = -1.0
        self.recentSwP = -1.0
        self.recentSwD = -1.0
        self.wvhtPercentileHistorical = -1.0
        self.wvhtPercentileRealtime = -1.0

    @staticmethod
    def buildSwellDirDict() -> dict:
        '''
        Builds dictionary to convert incoming swell direction strings to degrees for swell arrows

        incoming from S --> 0 
        incoming from W --> 90
        incoming from N --> 180
        incoming from E --> 270
    
        '''
        swellDirDict = dict()
        dirStrings = ['S', 'SSW', 'SW', 'WSW',
                      'W', 'WNW', 'NW', 'NNW',
                      'N', 'NNE', 'NE', 'ENE',
                      'E', 'ESE', 'SE', 'SSE']
        dirDegrees = np.arange(0, 382.5, 22.5)  # 0:22.5:360
        iCount = 0
        for iDir in dirStrings:
            swellDirDict[iDir] = dirDegrees[iCount]
            iCount = iCount + 1
    
        return swellDirDict

    def buildStationURLs(self) -> str:
        urlRealtime = f'{self.baseURLRealtime}{self.stationID}.spec'
        return urlRealtime

    def makeHistoricalDataRequest(self, year: int) -> requests.models.Response:
        historicalURL = f'https://www.ndbc.noaa.gov/view_text_file.php?filename={self.stationID}h{year}.txt.gz&dir=data/historical/stdmet/'
        print(f'requesting {historicalURL} after {self.nSecondsToPauseBtwnRequests}s pause...')
        time.sleep(self.nSecondsToPauseBtwnRequests)
        ndbcPage = requests.get(historicalURL)       #<class 'requests.models.Response'>
        return ndbcPage

    def makeRealtimeDataRequest(self) -> requests.models.Response:
        print(f'requesting {self.urlRealtime} after {self.nSecondsToPauseBtwnRequests}s pause...')
        time.sleep(self.nSecondsToPauseBtwnRequests)
        ndbcPage = requests.get(self.urlRealtime)       #<class 'requests.models.Response'>
        print(f'ndbcPage response for realtime data for station {self.stationID}: {ndbcPage}')
        if ndbcPage.status_code == 404:
            raise Exception(f'Could not connect to realtime data server for station {self.stationID}. This data might not exist for this station!')
        return ndbcPage

    @staticmethod
    def parseRealtimeData(ndbcPage) -> pd.DataFrame:
        #TODO: check other ways of doing this!!
        buoySoup = BeautifulSoup(ndbcPage.content, 'html.parser') #<class 'bs4.BeautifulSoup'>

        soupString = str(buoySoup)# convert soup to a string
        rowList = re.split("\n+", soupString)# split string based on row divisions
        rowList = rowList[:-1]# TODO: remove last entry if necessary
        entryList = [re.split(" +", iRow) for iRow in rowList]# split each row into a list of individual entries using spaces, so we have a list of lists
    
        # build data frame
        buoyDF = pd.DataFrame(entryList[2:], columns = entryList[0])  # ignore first 2 rows
        return buoyDF

    def setSamplingPeriod(self, buoyDF):
        dateSeries = buoyDF['Date']
        expectedInterval = pd.Timedelta(1, unit='hours')
        self.nSampsPerHour = 1
        thisInterval = dateSeries[0] - dateSeries[1]
        if thisInterval != expectedInterval:
            self.nSampsPerHour = round(expectedInterval.value / thisInterval.value)
            print(f'Detected sampling period of {thisInterval} instead of {expectedInterval} for this buoy! Setting self.nSamperPerHour to {self.nSampsPerHour}')


    def cleanRealtimeDataFrame(self, buoyDF):
        buoyDF['Date'] = buoyDF['#YY'] + buoyDF['MM'] + buoyDF['DD'] + buoyDF['hh'] + buoyDF['mm']# add a date column
        buoyDF['Date'] = pd.to_datetime(buoyDF['Date'], format='%Y%m%d%H%M')

        # drop unncessary columns
        buoyDF = buoyDF.loc[:, ['Date', 'WVHT', 'SwP', 'SwD']]
    
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
        self.setSamplingPeriod(self.dataFrameRealtime)
    
    def getHistoricalYears(self, nYears: int) -> list:
        todaysDate = date.today()
        currentYear = todaysDate.year
        return list(range(currentYear - nYears, currentYear))

    def getHistoricalMonths(self, nMonths: int) -> list:
        # months need to be in [1, 12]
        todaysDate = date.today()
        currentMonth = todaysDate.month
        nBackMonths = (nMonths - 1) // 2
        nForwardMonths = (nMonths - 1) // 2
        if nMonths % 2 == 0:
            nForwardMonths += 1

        return [(currentMonth + dMonth - 1) % 12 + 1 for dMonth in range(-nBackMonths, nForwardMonths+1)]

    @staticmethod
    def parseHistoricalData(ndbcPage, monthsToCheck: list[int]):
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
        buoyDF = buoyDF.drop(rowsToRemove.index)

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

    @staticmethod
    def cleanHistoricalDataFrame(buoyDF):
        # build date column
        buoyDF['Date'] = buoyDF['#YY'] + buoyDF['MM'] + buoyDF['DD'] + buoyDF['hh'] + buoyDF['mm']# add a date column
        buoyDF['Date'] = pd.to_datetime(buoyDF['Date'], format='%Y%m%d%H%M')

        # drop unneccessary columns and convert data types
        buoyDF = buoyDF.loc[:, ['Date', 'WVHT', 'DPD', 'MWD']]
        buoyDF["WVHT"] = pd.to_numeric(buoyDF["WVHT"])
        buoyDF["DPD"] = pd.to_numeric(buoyDF["DPD"])
        buoyDF["MWD"] = pd.to_numeric(buoyDF["MWD"])
        return buoyDF

    def buildHistoricalDataFrame(self):
        yearsToCheck = self.getHistoricalYears(self.nYearsBack)
        monthsToCheck = self.getHistoricalMonths(self.nHistoricalMonths)
        print(f'Grabbing historical data from years of {yearsToCheck} and months {monthsToCheck}')
        print(f'To limit requests to NDBC webpage, collecting {self.nYearsBack} years of historical data will take us about {self.nYearsBack * self.nSecondsToPauseBtwnRequests}s')
        historicalDataFrames = []
        for yearToCheck in yearsToCheck:
            ndbcPage = self.makeHistoricalDataRequest(yearToCheck)
            rawDF = self.parseHistoricalData(ndbcPage, monthsToCheck)
            thisDataFrame = self.cleanHistoricalDataFrame(rawDF)
            historicalDataFrames.append(thisDataFrame)

        self.dataFrameHistorical = pd.concat(historicalDataFrames)

    def setBuoyLocationFromDB(self, dBInteractor):
        print(f'Setting buoy location for station {self.stationID}')
        self.lat, self.lon = dBInteractor.getStationLocation(self.stationID)
        print(f'station {self.stationID} at ({self.lat, self.lon})')

    def setRealtimeDFFromDB(self, dBInteractor):
        print(f'Setting realtime dataframe for station {self.stationID}')
        self.dataFrameRealtime = dBInteractor.getRealtimeData(self.stationID)

    def setHistoricalDFFromDB(self, dBInteractor):
        self.dataFrameHistorical = dBInteractor.getHistoricalData(self.stationID)

    def setLocation(self, buoyLatLon: tuple[float]):
        self.lat, self.lon = buoyLatLon

    def fetchDataFromNDBCPage(self):
        self.buildRealtimeDataFrame()
        self.buildHistoricalDataFrame()

    def fetchDataFromDB(self) -> bool:
        dBInteractor = DatabaseInteractor()
        if not dBInteractor.successfulConnection:
            print('Connection failed so we cannot fetch any data')
            return False

        if not dBInteractor.checkForBuoyExistenceInDB(self.stationID):
            print(f'station {self.stationID} does not exist in database!')
            dBInteractor.closeConnection()
            return False

        self.setBuoyLocationFromDB(dBInteractor)
        self.setRealtimeDFFromDB(dBInteractor)
        self.setHistoricalDFFromDB(dBInteractor)

        dBInteractor.closeConnection()
        return True

    def setRecentReadings(self):
        self.recentWVHT = self.dataFrameRealtime['WVHT'].iloc[0]
        self.recentSwP = self.dataFrameRealtime['SwP'].iloc[0]
        self.recentSwD = self.dataFrameRealtime['SwD'].iloc[0]

    def calcWVHTPercentile(self, dataSetName: str) -> float:
        if dataSetName == 'historical':
            waveheightsSorted = self.dataFrameHistorical['WVHT'].sort_values().to_numpy() # ascending
        elif dataSetName == 'realtime':
            waveheightsSorted = self.dataFrameRealtime['WVHT'][1:].sort_values().to_numpy() # ascending
        else:
            raise ValueError('historical and realtime are the only supported data sets')

        nTotalValues = len(waveheightsSorted)
        ptr = 0
        while ptr < nTotalValues and self.recentWVHT > waveheightsSorted[ptr]:
            ptr += 1

        wvhtPercentile = ptr / nTotalValues * 100
        print(f'current swell of {self.recentWVHT: 0.2f} m is greater than {wvhtPercentile :0.1f}% of {dataSetName} data, ({nTotalValues} samples)')
        return wvhtPercentile

    def setWVHTPercentileHistorical(self):
        self.wvhtPercentileHistorical = self.calcWVHTPercentile('historical')

    def setWVHTPercentileRealtime(self):
        self.wvhtPercentileRealtime = self.calcWVHTPercentile('realtime')

    def buildAnalysisProducts(self):
        self.setRecentReadings()
        self.setWVHTPercentileHistorical()
        self.setWVHTPercentileRealtime()
        self.setSamplingPeriod(self.dataFrameRealtime)

    def convertRequestedDaysIntoSamples(self, nDays: int) -> int:
        if nDays > 44:
            print(f'Only have 44 days worth of realtime data so just plotting the last 45 days')
            nDays = 44
        nSamples = 24 * self.nSampsPerHour * nDays   
        return nSamples

    def getOrientedWvhtsAndDates(self, nSamples: int) -> tuple:
        # reverse so that the most recent sample is the last array value
        def truncateAndReverse(dataSeries: np.ndarray) -> np.ndarray:
            truncated = dataSeries[:nSamples]
            return truncated[::-1]

        return truncateAndReverse(self.dataFrameRealtime['WVHT'].to_numpy()), truncateAndReverse(self.dataFrameRealtime['Date'].to_numpy())

