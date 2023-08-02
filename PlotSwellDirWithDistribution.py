import argparse
from BuoyDataUtilities import getActiveBOI, truncateAndReverse, restricted_int
from PlottingUtilities import makeCircularHist, convertTimestampsToTimedeltas
from NDBCBuoy import NDBCBuoy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cmx
import traceback

def getRecentSwellDirData(buoy: NDBCBuoy, useDB: bool, nDays: int) -> tuple[np.ndarray]:
    if useDB:
        buoy.fetchDataFromDB()
        buoy.setSamplingPeriod(buoy.dataFrameRealtime)
    else:
        buoy.buildRealtimeDataFrame()

    nSamples = buoy.convertRequestedDaysIntoSamples(nDays)
    dates = truncateAndReverse(buoy.dataFrameRealtime['Date'].to_numpy(), nSamples)
    swd = truncateAndReverse(buoy.dataFrameRealtime['SwD'].to_numpy(), nSamples)
    return dates, swd

def getHistoricalSwellDirs(buoy: NDBCBuoy, useDB: bool) -> np.ndarray:
    if useDB:
        buoy.fetchDataFromDB()
    else:
        buoy.buildHistoricalDataFrame()

    swd = buoy.dataFrameHistorical['MWD'].to_numpy()
    return swd

def getArrowCoordinates(swd: np.ndarray, r0: float) -> np.ndarray:
    swdRad = np.deg2rad(swd)
    arrowCoords = np.zeros((4, len(swd)))
    arrowCoords[0, :] = swdRad + np.pi # arrow origin angle
    arrowCoords[1, :] = np.linspace(0.5 * r0, r0, len(swdRad)) # arrow origin radius
    arrowCoords[2, :] = np.sin(swdRad) # U 
    arrowCoords[3, :] = np.cos(swdRad) # V 

    return arrowCoords

def getArrowColors(timeDeltas: np.ndarray, scalarMap: cmx.ScalarMappable) -> list[tuple]:
    # map time deltas to [0, 1] 
    maxTime = max(timeDeltas)
    minTime = min(timeDeltas)
    arrowColors = [scalarMap.to_rgba((x - minTime) / (maxTime - minTime)) for x in timeDeltas]
    return arrowColors

def plotSwellDirs(dates: np.ndarray, swd: np.ndarray, historicalSwd: np.ndarray, stationID: str, showPlot: bool):
    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw=dict(projection='polar'))
    makeCircularHist(ax, np.deg2rad(historicalSwd))
    ax.set_title(f'Station {stationID} swell direction measurements on historical distribution')
    ax.grid(zorder=0)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(np.linspace(0, 2*np.pi, 8, endpoint=False))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
    #print(f'ylims = {ax.get_ylim()}')

    cmap = plt.get_cmap('viridis')  # Choose any colormap you like
    cNorm = mcolors.Normalize(vmin=0, vmax=1)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)
    arrowCoords = getArrowCoordinates(swd, ax.get_ylim()[1])
    timeDeltas = convertTimestampsToTimedeltas(dates)
    arrowColors = getArrowColors(timeDeltas, scalarMap)
    for idx in range(len(arrowColors)):
        ax.quiver(arrowCoords[0, idx], arrowCoords[1, idx], arrowCoords[2, idx], arrowCoords[3, idx], color=arrowColors[idx])

    scalarMap.set_array([])
    colorVals = np.linspace(0, 1, len(timeDeltas))
    tickIdxs = [0, round(len(timeDeltas)/3), round(2*len(timeDeltas)/3), len(timeDeltas)-1]
    cbar = fig.colorbar(scalarMap, ax=ax, ticks=[colorVals[idx] for idx in tickIdxs], label='Time delay [hrs]')
    cbar.ax.set_yticklabels([f'{timeDeltas[idx]:0.1f}' for idx in tickIdxs])
    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_recentswelldir_wdist.png', format='png')

def makeDirDistPlot(activeBOI: dict, useDB: bool, nDays: int, showPlots: bool):
    for stationID in activeBOI:
        try:
            dates, swd = getRecentSwellDirData(NDBCBuoy(stationID), useDB, nDays)
            historicalSwd = getHistoricalSwellDirs(NDBCBuoy(stationID), useDB)
        except Exception as e:
            print(f'---------')
            print(f'EXCEPTION: {e}')
            traceback.print_exc()
            print(f'---------')
            continue

        plotSwellDirs(dates, swd, historicalSwd, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")
    parser.add_argument("--nDays", type=restricted_int, required=True, help="# of recent days worth of measurements to include in plots [1-44]")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeDirDistPlot(activeBOI, args.db, args.nDays, args.show)

if __name__ == "__main__":
    main()

