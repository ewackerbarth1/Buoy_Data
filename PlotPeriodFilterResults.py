import argparse
from BuoyDataUtilities import getActiveBOI, getMonthlyDF
from NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getPercentageForThisMonth(df: pd.core.frame.DataFrame, month: int, minPeriod: float) -> float:
    monthDF = getMonthlyDF(df, month)
    percentThatMetThreshold = len(monthDF[monthDF['DPD'] >= minPeriod]) / len(monthDF) * 100
    return percentThatMetThreshold

def processHistoricalDataThroughPeriodFilter(buoy: NDBCBuoy, minPeriod: float) -> list:
    return [getPercentageForThisMonth(buoy.dataFrameHistorical, month, minPeriod) for month in range(1, 13)]

def plotPercentAboveThreshold(metThresholdPercentages: list, minPeriod: float, stationID: str, showPlot: bool):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, metThresholdPercentages, 'o-', color="royalblue", zorder=2)
    plt.title(f'% of station {stationID} measurements above {minPeriod:.1f} s period')
    plt.xlabel('Month')
    plt.ylabel('% above threshold')
    plt.ylim([-5, 105])
    plt.grid(zorder=1)

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_periodThreshold.png', format='png')

def makePeriodFilterPlots(activeBOI: dict, nYearsBack: int, showPlots: bool, minPeriod: float):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        metThresholdPercentages = processHistoricalDataThroughPeriodFilter(thisBuoy, minPeriod)
        print(f"met period threshold percentages = {[f'{x:.2f}' for x in metThresholdPercentages]}")
        plotPercentAboveThreshold(metThresholdPercentages, minPeriod, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makePeriodFilterPlots(activeBOI, args.nYears, args.show, args.minPeriod)

if __name__ == "__main__":
    main()
