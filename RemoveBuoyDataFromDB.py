import argparse
from ndbc_analysis_utilities.db_config.DatabaseInteractor import DatabaseInteractor
from ndbc_analysis_utilities.BuoyDataUtilities import parseBOIFile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="name of text file containing ids of buoys to remove from database")
    args = parser.parse_args()

    buoyList = parseBOIFile(args.bf)

    dbInteractor = DatabaseInteractor() 
    if not dbInteractor.successfulConnection:
        raise Exception("Unsuccessful attempt to connect to database")
    
    for stationID in buoyList:
        # check if buoy is in stations table
        if not dbInteractor.checkForBuoyExistenceInDB(stationID):
            print(f'station {stationID} is not in the database, so we do not need to remove it')
            continue

        # remove realtime entries, historical entries, stations table entry
        dbInteractor.removeRealtimeSamplesForStation(stationID)
        dbInteractor.removeHistoricalSamplesForStation(stationID)
        dbInteractor.removeStationsTableEntry(stationID)

    dbInteractor.connection.commit()
    dbInteractor.closeConnection()


if __name__ == "__main__":
    main()

