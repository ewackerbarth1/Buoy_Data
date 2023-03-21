import argparse
from DatabaseInteractor import DatabaseInteractor
from NDBCBuoy import NDBCBuoy
from BuoySelector import BuoySelector


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
        if not dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is not in the database, so please add it before attempting to update its data!')
            continue

        # if it is, then check whether the current data is outdated
        if not dbInteractor.isItTimeToUpdateRealtimeData(stationID):
            print(f'realtime data for {stationID} is still current!')
            continue

        # if it is, then request the most current data from NOAA
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.buildRealtimeDataFrame()

        # add realtime data set to realtime_data table
        dbInteractor.updateRealtimeDataEntry(stationID, thisBuoy.dataFrameRealtime)

    dbInteractor.closeConnection()

def updateHistoricalData(args):
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
        if not dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is not in the database, so please add it before attempting to update its data!')
            continue

        # if it is, check whether it's time to update the historical data
        if not dbInteractor.isItTimeToUpdateHistoricalData(stationID):
            print(f'historical data for {stationID} is still applicable!')
            continue

        # if it is, then get realtime data set for it 
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.buildHistoricalDataFrame()

        # add realtime data set to realtime_data table
        dbInteractor.updateHistoricalDataEntry(stationID, thisBuoy.dataFrameHistorical)

    dbInteractor.closeConnection()

def addDesiredBuoysToDB(args):
    desiredLocation = (args.lat, args.lon)
    myBuoySelector = BuoySelector(desiredLocation, args.bf)
    myBuoySelector.setActiveBuoys()
    myBuoySelector.getBuoysOfInterest()

    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        print('Could not add buoys because of unsuccessful connection')
        return

    for stationID, latLon in myBuoySelector.activeBOI.items():
        if dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is already in the database!')
        else:
            print(f'adding station {stationID} to database...')
            dbInteractor.addBuoyToStationsTable(stationID, latLon)

    dbInteractor.printContentsOfStationsTable()
    dbInteractor.closeConnection()

def getBuoyLocations(args):
    desiredLocation = (args.lat, args.lon)
    myBuoySelector = BuoySelector(desiredLocation, args.bf)
    boiList = myBuoySelector.parseBOIFile()

    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        print('Could not complete database action because of unsuccessful connection')
        return

    for stationID in boiList:
        stationLoc = dbInteractor.getStationLocation(stationID)
        print(f'station {stationID} is located at {stationLoc}')

    dbInteractor.closeConnection()

def makeBuoyPicture(args: argparse.Namespace):
    desiredLocation = (args.lat, args.lon)
    myBuoySelector = BuoySelector(desiredLocation, args.bf, args.db)
    myBuoySelector.buildBOIDF()
    myBuoySelector.mapBuoys()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--action", type=str, required=True, help="update-data or display-map")
    parser.add_argument("--db", type=bool, required=False, default=True, help="default True, set False to not use a database")

    args = parser.parse_args()

    if args.action == 'update-data':
        if not args.db:
            print(f'Not using database so there is no update-data action!')
            return
        addDesiredBuoysToDB(args)
        updateRealtimeData(args)
        updateHistoricalData(args)
    elif args.action == 'display-map':
        makeBuoyPicture(args)
    else:
        ValueError('Invalid input for action argument! Valid inputs are: update-data or display-data')

if __name__ == "__main__":
    main()
