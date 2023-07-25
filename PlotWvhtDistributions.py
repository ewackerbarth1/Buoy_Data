import argparse
from NDBCBuoy import NDBCBuoy
from BuoyDataUtilities import getActiveBOI, calcDistanceBetweenNM, convertDistanceToSwellETA, calculateBearingAngle

def makeWVHTDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    nDaysToInclude = 4
    minSwellPeriod, maxSwellPeriod = 12, 18
    currentLoc = (args.lat, args.lon)
    for stationID, stationLatLon in activeBOI.items():
        print(f'Instantiating NDBCBuoy {stationID}...')
        thisBuoy = NDBCBuoy(stationID)

        if args.db:
            fetchSuccess = thisBuoy.fetchDataFromDB()
            if not fetchSuccess:
                print(f'Unable to fetch data for station {stationID} from database')
                continue
        else:
            thisBuoy.setLocation(stationLatLon)
            thisBuoy.fetchDataFromNDBCPage()

        thisBuoy.buildAnalysisProducts()

        # set arrival window
        distanceAway = calcDistanceBetweenNM(currentLoc, stationLatLon)
        maxArrivalLag = convertDistanceToSwellETA(minSwellPeriod, distanceAway)
        minArrivalLag = convertDistanceToSwellETA(maxSwellPeriod, distanceAway)
        thisBuoy.setArrivalWindow((minArrivalLag, maxArrivalLag))

        bearingAngle = calculateBearingAngle(stationLatLon, currentLoc)  # from buoy to current location in degrees
        thisBuoy.makeWvhtDistributionPlot(nDaysToInclude, bearingAngle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeWVHTDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()
