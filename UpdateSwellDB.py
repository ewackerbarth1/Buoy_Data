import argparse
from ndbc_analysis_utilities.db_config.DatabaseInteractor import DatabaseInteractor
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI

def updateRealtimeData(activeBOI: dict):
    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        raise Exception("Unsuccessful attempt to connect to database")

    for stationID in activeBOI:
        # check if buoy is in stations table
        if not dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is not in the database, so please add it before attempting to update its data!')
            continue

        # if buoy is in stations table, then check whether the current data is outdated
        if not dbInteractor.isItTimeToUpdateRealtimeData(stationID):
            print(f'realtime data for {stationID} is still current')
            continue

        # if time for update, then request current data from NOAA
        thisBuoy = NDBCBuoy(stationID)
        try:
            thisBuoy.buildRealtimeDataFrame()
        except Exception as e:
            print('-------')
            print(f'EXCEPTION: {e}')
            print('-------')
            print(f'Failed to build realtime data frame for station {stationID}!!!')
            continue

        # add realtime data set to realtime_data table
        dbInteractor.updateRealtimeDataEntry(stationID, thisBuoy.dataFrameRealtime)

    dbInteractor.closeConnection()

def updateHistoricalData(activeBOI: dict):
    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        raise Exception("Unsuccessful attempt to connect to database")

    for stationID in activeBOI:
        # check if buoy is in stations table
        if not dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is not in the database, so please add it before attempting to update its data!')
            continue

        # if it is, check whether it's time to update the historical data
        if not dbInteractor.isItTimeToUpdateHistoricalData(stationID):
            print(f'historical data for {stationID} is still applicable')
            continue

        # if it's time to update, then get historical data set for the buoy
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.buildHistoricalDataFrame()

        # add historical data set to historical_data table
        dbInteractor.updateHistoricalDataEntry(stationID, thisBuoy.dataFrameHistorical)

    dbInteractor.closeConnection()

def addDesiredBuoysToDB(activeBOI: dict):
    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        raise Exception("Unsuccessful attempt to connect to database")

    for stationID, latLon in activeBOI.items():
        if dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is already in the database')
        else:
            print(f'adding station {stationID} to database...')
            dbInteractor.addBuoyToStationsTable(stationID, latLon)

    dbInteractor.printContentsOfStationsTable()
    dbInteractor.closeConnection()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="name of text file containing buoys of interest")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    addDesiredBuoysToDB(activeBOI)
    updateRealtimeData(activeBOI)
    updateHistoricalData(activeBOI)

if __name__ == "__main__":
    main()


