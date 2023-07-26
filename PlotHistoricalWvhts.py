import argparse
from BuoyDataUtilities import getActiveBOI
from NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getMonthlyData(df: pd.core.frame.DataFrame, month: int) -> np.ndarray:
    # select samples of df that correspond to desired month
    monthlyDF = df[df['Date'].dt.month == month]
    wvhts = monthlyDF['WVHT'].to_numpy()
    return wvhts

def getPercentileSample(wvhts: np.ndarray, nthPercentile: int) -> np.float64:
    nSamples = len(wvhts)
    ithSample = int(np.ceil(nthPercentile / 100 * nSamples) - 1)
    sortedWvhts = np.sort(wvhts)
    return sortedWvhts[ithSample]

def processHistoricalData(buoy: NDBCBuoy) -> list:
    percentileData = [[], []]
    for month in range(1, 13):
        monthlyData = getMonthlyData(buoy.dataFrameHistorical, month)
        percentileData[0].append(getPercentileSample(monthlyData, 50))
        percentileData[1].append(getPercentileSample(monthlyData, 90))

    return percentileData

def plotWvhts(percentileData: list, stationID: str, showPlot: bool):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, percentileData[0], 'o-', color="royalblue", label='50th %')
    plt.plot(months, percentileData[1], 'o-', color="seagreen", label='90th %')
    plt.title(f'Historical Wvhts for station {stationID}')
    plt.xlabel('Month')
    plt.ylabel('Wvht [m]')
    plt.grid()
    plt.legend()

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_historicalwvhts.png', format='png')

def mainFunction(activeBOI: dict, nYearsBack: int, showPlots: bool):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        percentileData = processHistoricalData(thisBuoy)

        plotWvhts(percentileData, stationID, showPlots)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    mainFunction(activeBOI, args.nYears, args.show)

if __name__ == "__main__":
    main()

