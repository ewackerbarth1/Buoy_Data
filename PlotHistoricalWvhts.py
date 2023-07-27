import argparse
from BuoyDataUtilities import getActiveBOI
from NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getMonthlyDF(df: pd.core.frame.DataFrame, month: int) -> pd.core.frame.DataFrame:
    return df[df['Date'].dt.month == month]

def getDataThatMetPeriodThresholds(df: pd.core.frame.DataFrame, minPeriod: float) -> tuple[pd.core.frame.DataFrame, float]:
    metThresholdData = df[df['DPD'] >= minPeriod]
    percentThatMetThreshold = len(metThresholdData) / len(df) * 100
    return metThresholdData, percentThatMetThreshold

def getMonthlyData(df: pd.core.frame.DataFrame, month: int, minPeriod: float) -> tuple[np.ndarray, float]:
    # select samples of df that correspond to desired month
    monthlyDF, thresholdPercentage = getDataThatMetPeriodThresholds(getMonthlyDF(df, month), minPeriod)
    wvhts = monthlyDF['WVHT'].to_numpy()
    return wvhts, thresholdPercentage

def getPercentileSample(wvhts: np.ndarray, nthPercentile: int) -> np.float64:
    nSamples = len(wvhts)
    ithSample = int(np.ceil(nthPercentile / 100 * nSamples) - 1)
    sortedWvhts = np.sort(wvhts)
    return sortedWvhts[ithSample]

def processHistoricalData(buoy: NDBCBuoy, minPeriod: float) -> tuple:
    percentileData = [[], []]
    metPeriodThresholdPercentages = []
    for month in range(1, 13):
        monthlyData, thresholdPercentage = getMonthlyData(buoy.dataFrameHistorical, month, minPeriod)
        metPeriodThresholdPercentages.append(thresholdPercentage)
        percentileData[0].append(getPercentileSample(monthlyData, 50))
        percentileData[1].append(getPercentileSample(monthlyData, 90))

    print(f"met period threshold percentages = {[f'{x:.2f}' for x in metPeriodThresholdPercentages]}")
    return percentileData, metPeriodThresholdPercentages

def transformData(data: list, currentRange: tuple, newRange: tuple) -> list:
    # transforms data from currentRange to newRange
    a, b = currentRange
    c, d = newRange
    scalingFactor = (d - c) / (b - a)
    shiftAmount = c
    markerSizes = [scalingFactor * (x - a) + shiftAmount for x in data]
    return markerSizes

def plotWvhts(percentileData: list, stationID: str, showPlot: bool, markerSizeData: list, minPeriod: float):
    markerSizeRange = (10, 100)
    markerSizes = transformData(markerSizeData, (0, 100), markerSizeRange)
    print(f"markerSizes = {[f'{m:.2f}' for m in markerSizes]}")
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, percentileData[0], '-', color="royalblue", label='_nolegend_', zorder=3)
    plt.plot(months, percentileData[1], '-', color="seagreen", label='_nolegend_', zorder=3)
    plt.scatter(months, percentileData[0], markerSizes, marker='o', color="royalblue", label='50th %', zorder=2)
    plt.scatter(months, percentileData[1], markerSizes, marker='o', color="seagreen", label='90th %', zorder=2)
    plt.title(f'Historical Wvhts for station {stationID} with min {minPeriod} s period')
    plt.xlabel('Month')
    plt.ylabel('Wvht [m]')
    plt.grid(zorder=1)

    plt.scatter([], [], markerSizeRange[1], color="black", label="100% of samples passed")
    plt.scatter([], [], (markerSizeRange[1] - markerSizeRange[0]) / 2, color="black", label="50% of samples passed")
    plt.legend()

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_historicalwvhts.png', format='png')


def plotWvhtsForStations(activeBOI: dict, nYearsBack: int, showPlots: bool, minPeriod: float):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        percentileData, metThresholdPercentages = processHistoricalData(thisBuoy, minPeriod)

        plotWvhts(percentileData, stationID, showPlots, metThresholdPercentages, minPeriod)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, default=0.0, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    plotWvhtsForStations(activeBOI, args.nYears, args.show, args.minPeriod)

if __name__ == "__main__":
    main()

