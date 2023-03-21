import requests
from bs4 import BeautifulSoup
from scipy.stats import norm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re
import warnings
import time
from datetime import date, datetime, timedelta
from BuoyDataUtilities import makeCircularHist
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
        self.arrivalWindow = []

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

    def setArrivalWindow(self, arrivalWindow: tuple[float]):
        self.arrivalWindow = arrivalWindow

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
        self.checkSamplingPeriod(self.dataFrameRealtime)

    @staticmethod
    def getHistoricalYearsAndMonths(nYears: int) -> tuple:
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
        yearsToCheck, monthsToCheck = self.getHistoricalYearsAndMonths(self.nYearsBack)
        print(f'Grabbing historical data from years of {yearsToCheck} and months {monthsToCheck}')
        print(f'To limit requests to NDBC webpage, collecting {len(yearsToCheck)} years of historical data will take us about {len(yearsToCheck)*5}s')
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
        self.checkSamplingPeriod(self.dataFrameRealtime)

    def convertRequestedDaysIntoSamples(self, nDays: int) -> int:
        if nDays > 44:
            print(f'Only have 44 days worth of realtime data so just plotting the last 45 days')
            nDays = 44
        nSamples = 24 * self.nSampsPerHour * nDays   
        return nSamples

    def getOrientedWvhtsAndDates(self, nSamples: int) -> tuple[pd.Series]:
        waveheights = self.dataFrameRealtime['WVHT']
        sampleDates = self.dataFrameRealtime['Date']
        waveheights = waveheights[:nSamples]
        sampleDates = sampleDates[:nSamples]
        waveheights = waveheights[::-1]  # reverse so that the most recent sample is the last array value
        sampleDates = sampleDates[::-1]
        return waveheights, sampleDates
    
    @staticmethod
    def estimateDensityGaussianKernel(data: np.ndarray[np.float64]) -> tuple:
        xd = np.linspace(0, max(data), 100)
        density = sum(norm(xi).pdf(xd) for xi in data)
        density = density / (sum(density) * (xd[1]-xd[0]))
        return xd, density

    @staticmethod
    def estimateDensityTophatKernel(data: np.ndarray[np.float64], binWidth: float) -> tuple:
        xd = np.linspace(0, max(data), 100)
        density = np.zeros(xd.shape)
        for xi in data:
            densityIdxs = abs(xi - xd) < 0.5*binWidth
            density[densityIdxs] += 1
    
        density = density / (sum(density) * (xd[1] - xd[0]))
        return xd, density

    @staticmethod
    def getNthPercentileSample(samplingVector: np.ndarray[np.float64], pmf: np.ndarray[np.float64], nthPercentile: float) -> np.float64:
        mass = 0
        sampleIdx = 0
        samplingBinWidth = samplingVector[1] - samplingVector[0]
        while mass < nthPercentile / 100 and sampleIdx < len(samplingVector):
            mass += pmf[sampleIdx] * samplingBinWidth
            sampleIdx += 1

        return samplingVector[sampleIdx]
    
    @staticmethod
    def convertTimestampsToTimedeltas(timestamps: np.ndarray[np.datetime64]) -> np.ndarray[np.float64]:
        now = np.datetime64('now')
        deltas = now - timestamps
        deltas = deltas.astype('timedelta64[h]')
        deltas = -1 * deltas.astype('float')
        return deltas

    @staticmethod
    def getXTicksForTimeDeltas(timeDeltas: np.ndarray[np.float64]) -> list[float]:
        minTimeDelta = min(timeDeltas)
        xTicks = []
        q, r = divmod(int(minTimeDelta), 24)
        nTicks = -1 * q
        if r == 0:
            nTicks += 1
            tickValue = q * 24
        else:
            tickValue = (q + 1) * 24

        for iTick in range(nTicks):
            xTicks.append(tickValue)
            tickValue += 24

        return xTicks


    def makeWvhtDistributionPlot(self, nDays: int):
        nSamples = self.convertRequestedDaysIntoSamples(nDays)
        waveheights, sampleDates = self.getOrientedWvhtsAndDates(nSamples)
        #print(f'sampleDates type = {type(sampleDates)}, {type(sampleDates[0])}')
        sampleTimedeltas = self.convertTimestampsToTimedeltas(sampleDates.to_numpy())
        #print(f'sampleTimedeltas type = {type(sampleTimedeltas)}, {type(sampleTimedeltas[0])}')

        rtSamplingVector, rtDist = self.estimateDensityTophatKernel(self.dataFrameRealtime['WVHT'].to_numpy(), 0.5)
        hSamplingVector, hDist = self.estimateDensityTophatKernel(self.dataFrameHistorical['WVHT'].to_numpy(), 0.5)

        h50thPercentileWvht = self.getNthPercentileSample(hSamplingVector, hDist, 50)
        h90thPercentileWvht = self.getNthPercentileSample(hSamplingVector, hDist, 90)
        print(f'50th percentile wvht for station {self.stationID} = {h50thPercentileWvht: 0.2f} m')
        print(f'90th percentile wvht for station {self.stationID} = {h90thPercentileWvht: 0.2f} m')

        print(f'min time lag = {self.arrivalWindow[0]: 0.2f}hrs, max time lag = {self.arrivalWindow[1]: 0.2f}hrs')
        arrivalWindow = [-1 * x for x in self.arrivalWindow]

        fig = plt.figure(figsize=(13, 7))
        ax = fig.add_gridspec(top=0.95, right=0.75).subplots()
        ax2 = ax.inset_axes([1.05, 0, 0.25, 1], sharey=ax)
        
        ax.plot(sampleTimedeltas, waveheights, 'o-', color='royalblue', label='wvht')
        xMin, xMax = min(sampleTimedeltas), max(sampleTimedeltas)
        print(f'min time delta = {xMin}, max time delta = {xMax}')
        ax.hlines(h50thPercentileWvht, xMin, xMax, color='seagreen', ls=':', alpha=0.9, label='50th %')
        ax.hlines(h90thPercentileWvht, xMin, xMax, color='seagreen', ls='--', alpha=0.9, label='90th %')
        ax.fill_betweenx([min(waveheights), max(waveheights)], arrivalWindow[1], arrivalWindow[0], color='darkblue', alpha=0.4, label='currently arriving')
        ax.set_ylabel('Wave height [m]')
        ax.set_xlabel('Sample time deltas [hrs]')
        ax.set_xticks(self.getXTicksForTimeDeltas(sampleTimedeltas))
        #ax.tick_params(axis='x', labelrotation=45, labelsize=7)
        ax.legend()
        ax.set_title(f'Station {self.stationID} waveheights')
        ax.grid()

        #ax2.plot(rtDist, rtSamplingVector, color='darkorange', label='realtime')
        #ax2.plot(hDist, hSamplingVector, color='seagreen', label='historical')
        ax2.fill_betweenx(rtSamplingVector, rtDist, 0, color='darkorange', alpha = 0.7, label='realtime')
        ax2.fill_betweenx(hSamplingVector, hDist, 0, color='seagreen', alpha = 0.7, label='historical')
        ax2.tick_params(axis='y', labelleft=False)
        ax2.legend(loc='upper left')
        xMin, xMax = ax2.get_xlim()
        ax2.set_xlim((xMax, xMin))
        ax2.set_xlabel('Density')
        ax2.grid()
        #manager = plt.get_current_fig_manager()
        #manager.full_screen_toggle()
        plt.savefig(f'station_{self.stationID}.png', format='png')
        #plt.show()

    def plotPastNDaysWvht(self, nDays: int):
        nSamples = self.convertRequestedDaysIntoSamples(nDays)
        waveheights, sampleDates = self.getOrientedWvhtsAndDates(nSamples)

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

