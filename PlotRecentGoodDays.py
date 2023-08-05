import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, truncateAndReverse, restricted_nDays_int, getNthPercentileSampleWithoutPMF
from ndbc_analysis_utilities.PlottingUtilities import convertTimestampsToTimedeltas, getColors
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cmx
import traceback

def getRecentWvhtsAndPeriods(buoy: NDBCBuoy, nDays: int) -> tuple[np.ndarray]:
    nSamples = buoy.convertRequestedDaysIntoSamples(nDays)
    columnNames = ['Date', 'WVHT', 'SwP']
    dataContainer = []
    for colName in columnNames:
        dataContainer.append(truncateAndReverse(buoy.dataFrameRealtime[colName].to_numpy(), nSamples))
    return dataContainer[0], dataContainer[1], dataContainer[2]

def calcNumGoodDays(df: pd.core.frame.DataFrame, minWvht: float, minPeriod: float) -> int:
    goodMeasurements = df[(df['SwP'] >= minPeriod) & (df['WVHT'] >= minWvht)]
    goodDays = set()
    for idx, row in goodMeasurements.iterrows():
        thisMonth, thisDay = row['Date'].day, row['Date'].month
        goodDays.add(f'{thisMonth}, {thisDay}')

    return len(goodDays)

def plotRecentData(dates: np.ndarray, wvhts: np.ndarray, swp: np.ndarray, stationID: str, showPlot: bool, minPeriod: float, minWvht: float, nDays: int, nGoodDays: int):
    fig, ax = plt.subplots(figsize=(14, 7))

    cmap = plt.get_cmap('viridis')  # Choose any colormap you like
    cNorm = mcolors.Normalize(vmin=0, vmax=1)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)
    timeDeltas = convertTimestampsToTimedeltas(dates)
    markerColors = getColors(timeDeltas, scalarMap)

    xMax = max(20, max(swp) + 1)
    yMax = max(wvhts) + 0.5
    ax.scatter(swp, wvhts, color=markerColors, zorder=2)
    ax.vlines(minPeriod, minWvht, yMax, color="purple", zorder=1)
    ax.hlines(minWvht, minPeriod, xMax, color="purple", zorder=1)
    ax.set_xlabel('Period [s]')
    ax.set_ylabel('Wvht [m]')
    ax.set_title(f'Prior {nDays} days at station {stationID}')
    ax.set_xlim([0, xMax])
    ax.set_ylim([0, yMax])
    #ax.grid(zorder=0)

    # text with number of good days in top right
    ax.text(0.63, 0.97, f'{nGoodDays} out of {nDays} days contained good measurements', transform=ax.transAxes, fontsize=8, zorder=1)

    # colorbar arrangement
    scalarMap.set_array([])
    colorVals = np.linspace(0, 1, len(timeDeltas))
    tickIdxs = [0, round(len(timeDeltas)/3), round(2*len(timeDeltas)/3), len(timeDeltas)-1]
    cbar = fig.colorbar(scalarMap, ax=ax, ticks=[colorVals[idx] for idx in tickIdxs], label='Time delay [days]')
    cbar.ax.set_yticklabels([f'{timeDeltas[idx]/24:0.1f}' for idx in tickIdxs])
    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_recentgooddays.png', format='png')

def makeGoodSamplesPlots(activeBOI: dict, args: argparse.Namespace):
    for stationID in activeBOI:
        buoy = NDBCBuoy(stationID)
        try:
            buoy.fetchData(args.db)
        except Exception as e:
            print(f'---------')
            print(f'EXCEPTION: {e}')
            traceback.print_exc()
            print(f'---------')
            continue

        dates, wvhts, swp = getRecentWvhtsAndPeriods(buoy, args.nDays)
        minWvht = getNthPercentileSampleWithoutPMF(buoy.dataFrameHistorical['WVHT'].to_numpy(), args.wvhtPer)
        nGoodDays = calcNumGoodDays(buoy.dataFrameRealtime.head(len(dates)), minWvht, args.minPeriod)
        plotRecentData(dates, wvhts, swp, stationID, args.show, args.minPeriod, minWvht, args.nDays, nGoodDays)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")
    parser.add_argument("--nDays", type=restricted_nDays_int, required=True, help="# of recent days worth of measurements to include in plots [1-44]")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum period [s] for good measurement threshold")
    parser.add_argument("--wvhtPer", type=float, required=True, help="minimum percentile [0-100] of waveheights for good measurement threshold")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeGoodSamplesPlots(activeBOI, args)

if __name__ == "__main__":
    main()

