import argparse
from BuoyDataUtilities import getActiveBOI, truncateAndReverse, restricted_nDays_int
from NDBCBuoy import NDBCBuoy
import numpy as np
import matplotlib.pyplot as plt
import traceback

def getRecentSwellData(buoy: NDBCBuoy, useDB: bool, nDays: int) -> tuple[np.ndarray]:
    if useDB:
        buoy.fetchDataFromDB()
    else:
        buoy.buildRealtimeDataFrame()

    nSamples = buoy.convertRequestedDaysIntoSamples(nDays)
    columnNames = ['Date', 'WVHT', 'SwP', 'SwD']
    dataContainer = []
    for colName in columnNames:
        dataContainer.append(truncateAndReverse(buoy.dataFrameRealtime[colName].to_numpy(), nSamples))
    return dataContainer[0], dataContainer[1], dataContainer[2], dataContainer[3] 

def convertSwdToUV(swd: list):
    # we want the x-coordinate of our arrow to evolve as sin(x)
    # we want the y-coordinate to evolve as cos(x)
    swdRad = np.deg2rad(swd)
    U = np.sin(swdRad)
    V = np.cos(swdRad)
    return U, V

def plotRecentData(dates: np.ndarray, wvhts: np.ndarray, swp: np.ndarray, swd: np.ndarray, stationID: str, showPlot: bool):
    nRows, nCols = 3, 1
    fig, ax = plt.subplots(3, sharex=True, figsize=(14, 7))
    ax[0].plot(dates, wvhts, 'o-', color="royalblue", zorder=1)
    ax[0].set_ylabel('Wvht [m]')
    ax[0].grid(zorder=0)

    ax[1].plot(dates, swp, 'o-', color="royalblue", zorder=1)
    ax[1].set_ylabel('Period [s]')
    ax[1].grid(zorder=0)

    U, V = convertSwdToUV(swd)
    ax[2].quiver(dates, np.zeros(np.shape(dates)), U, V, angles='uv', scale=100.0)
    ax[2].set_xlabel('Timestamps')
    ax[2].set_ylim([-1, 1])

    subplotTitles = ['Wave Heights', 'Period', 'Direction']
    for rIdx in range(nRows):
        ax[rIdx].set_title(subplotTitles[rIdx])

    fig.suptitle(f"Station {stationID} swell data")
    fig.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9, hspace=0.3)

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_recentswelldata.png', format='png')

def makeRecentPlots(activeBOI: dict, useDB: bool, nDays: int, showPlots: bool):
    for stationID in activeBOI:
        try:
            dates, wvhts, swp, swd = getRecentSwellData(NDBCBuoy(stationID), useDB, nDays)
        except Exception as e:
            print(f'---------')
            print(f'EXCEPTION: {e}')
            traceback.print_exc()
            print(f'---------')
            continue

        plotRecentData(dates, wvhts, swp, swd, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")
    parser.add_argument("--nDays", type=restricted_nDays_int, required=True, help="# of recent days worth of measurements to include in plots [1-44]")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeRecentPlots(activeBOI, args.db, args.nDays, args.show)

if __name__ == "__main__":
    main()
