import pandas as pd
import time
from datetime import date, datetime, timedelta
import config_local as config
import pymysql
import sys

def convertDFToJSONStr(df):
    return df.to_json(date_format='iso', orient='records')

def convertJSONStrToDF(jsonStr):
    return pd.read_json(jsonStr, orient='records', convert_dates=['Date'])

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

        print(f'buoyDF = {buoyRealtimeDataframe}')
        # convert data frame to JSON string
        dfJSONStr = convertDFToJSONStr(buoyRealtimeDataframe)
        print(f'Size of json string = {sys.getsizeof(dfJSONStr)}')

        # write station id and JSON string to v2 table
        sqlCmd = 'INSERT INTO realtime_data (station_id, data) VALUES (%s, %s)'
        thisCursor.execute(sqlCmd, (stationID, dfJSONStr))

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

    def removeHistoricalSamplesForStation(self, stationID):
        thisCursor = self.connection.cursor()
        thisCursor.execute('DELETE FROM historical_data WHERE station_id = %s', (stationID,))
        thisCursor.close()

    def addHistoricalSamplesForStation(self, stationID, buoyDF):
        thisCursor = self.connection.cursor()

        print(f'buoyDF = {buoyDF}')
        # convert data frame to JSON string
        dfJSONStr = convertDFToJSONStr(buoyDF)
        print(f'Size of json string = {sys.getsizeof(dfJSONStr)}')

        # write station id and JSON string to v2 table
        sqlCmd = 'INSERT INTO historical_data (station_id, data) VALUES (%s, %s)'
        thisCursor.execute(sqlCmd, (stationID, dfJSONStr))

        thisCursor.close()

    def updateHistoricalDataEntry(self, stationID, buoyDF):
        print(f'Removing historical data for station {stationID}')
        startTime = time.time()
        self.removeHistoricalSamplesForStation(stationID)
        print(f'Removing historical data took {time.time() - startTime} s')

        print(f'Adding historical data for station {stationID}')
        startTime = time.time()
        self.addHistoricalSamplesForStation(stationID, buoyDF)
        print(f'Adding historical data took {time.time() - startTime} s')
        
        self.connection.commit()
        print(f'Updated historical data for station {stationID}')

    def getStationLocation(self, stationID: str) -> tuple[float]:
        thisCursor = self.connection.cursor()
        sqlCmd = 'SELECT ST_X(location) as latitude, ST_Y(location) as longitude FROM stations WHERE id = %s'
        thisCursor.execute(sqlCmd, (stationID,))
        stationLoc = thisCursor.fetchone()
        thisCursor.close()
        return stationLoc

    def getRealtimeData(self, stationID):
        thisCursor = self.connection.cursor()
        sqlCmd = 'SELECT data FROM realtime_data WHERE station_id = %s'
        thisCursor.execute(sqlCmd, (stationID,))
        realtimeJSONStr = thisCursor.fetchone()[0]
        thisCursor.close()

        #print(f'realtime data JSON str for station {stationID}:')
        #print(realtimeJSONStr)
        realtimeDF = convertJSONStrToDF(realtimeJSONStr)
        return realtimeDF

    def getLastTableUpdateTimestamp(self, tableName: str, stationID: str):
        thisCursor = self.connection.cursor()
        sqlCmd = f'SELECT created_at FROM {tableName} WHERE station_id = %s'
        thisCursor.execute(sqlCmd, (stationID,))

        timestamps = thisCursor.fetchone()
        thisCursor.close()
        if timestamps is None:
            print(f'No {tableName} entry for station {stationID}')
            return None 

        timestamp = timestamps[0]
        print(f'last {tableName} update for station {stationID} at {timestamp}')
        return timestamp

    def isItTimeToUpdateRealtimeData(self, stationID: str) -> bool:
        updatePeriodInHours = 1
        updatePeriod = timedelta(hours=updatePeriodInHours)

        lastUpdateTimeStamp = self.getLastTableUpdateTimestamp('realtime_data', stationID)
        if lastUpdateTimeStamp is None:
            return True
        currentTimestamp = datetime.now()
        timeSinceLastUpdate = currentTimestamp - lastUpdateTimeStamp
        print(f'Time since last realtime data update for station {stationID} = {timeSinceLastUpdate}')

        if timeSinceLastUpdate > updatePeriod:
            return True
        else:
            return False

    def isItTimeToUpdateHistoricalData(self, stationID: str) -> bool:
        lastUpdateTimeStamp = self.getLastTableUpdateTimestamp('historical_data', stationID)
        if lastUpdateTimeStamp is None:
            return True

        lastUpdateMonth = lastUpdateTimeStamp.month
        print(f'Last historical data update for station {stationID} was in month {lastUpdateMonth}')
        currentMonth = datetime.now().month

        if lastUpdateMonth != currentMonth:
            return True
        else:
            return False

    def getHistoricalData(self, stationID):
        thisCursor = self.connection.cursor()
        sqlCmd = 'SELECT data FROM historical_data WHERE station_id = %s'
        thisCursor.execute(sqlCmd, (stationID,))
        historicalJSONStr = thisCursor.fetchone()[0]
        thisCursor.close()

        historicalDF = convertJSONStrToDF(historicalJSONStr)
        return historicalDF

    def closeConnection(self):
        self.connection.close()

