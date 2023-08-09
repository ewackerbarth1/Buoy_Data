import argparse
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
from ndbc_analysis_utilities.BuoyDataUtilities import parseBOIFile, getActiveNDBCStations
import os

def makeDataRequest(stationID: str) -> bool:
    try:
        buoy = NDBCBuoy(stationID)
        buoy.makeRealtimeDataRequest()
    except Exception as e:
        print(f'EXCEPTION: {e}')
        return False

    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")

    args = parser.parse_args()

    desiredStations = parseBOIFile(args.bf)
    activeStations = getActiveNDBCStations() 
    stationsToKeep = [] 
    stationsToRemove = []
    for station in desiredStations:
        if station not in activeStations:
            stationsToRemove.append(station)
            continue

        # make realtime data request
        if not makeDataRequest(station):
            stationsToRemove.append(station)
            continue

        stationsToKeep.append(station)


    name, extension = os.path.splitext(args.bf)

    # write stationsToKeep to file
    keepFName = f'{name}_keep.txt'
    if len(stationsToKeep) > 0:
        print(f'Writing  {keepFName} ...')
        with open(keepFName, 'w') as f:
            f.write('\n'.join(stationsToKeep))
    else:
        print('No valid stations to keep!')

    # write stationsToRemove to file
    removeFName = f'{name}_remove.txt'
    if len(stationsToRemove) > 0:
        print(f'Writing {removeFName} ...')
        with open(removeFName, 'w') as f:
            f.write('\n'.join(stationsToRemove))
    else:
        print('All stations are valid!')

if __name__ == "__main__":
    main()
