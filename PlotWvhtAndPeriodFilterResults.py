import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, getMonthlyDF
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getJointPercentage(monthDF: pd.core.frame.DataFrame, minPeriod: float, minWvht: float) -> float:
    percentThatMetThreshold = len(monthDF[(monthDF['DPD'] >= minPeriod) & (monthDF['WVHT'] >= minWvht)]) / len(monthDF) * 100
    return percentThatMetThreshold

def getMeasurementPercentage(monthDF: pd.core.frame.DataFrame, colName: str, minValue: float) -> float:
    percentThatMetThreshold = len(monthDF[monthDF[colName] >= minValue]) / len(monthDF) * 100
    return percentThatMetThreshold

def processHistoricalDataThroughFilter(df: pd.core.frame.DataFrame, minPeriod: float, minWvht: float) -> list:
    jointResults, periodResults, wvhtResults = [], [], []
    for month in range(1, 13):
        monthDF = getMonthlyDF(df, month)
        jointResults.append(getJointPercentage(monthDF, minPeriod, minWvht))
        periodResults.append(getMeasurementPercentage(monthDF, 'DPD', minPeriod))
        wvhtResults.append(getMeasurementPercentage(monthDF, 'WVHT', minWvht))

    return jointResults, periodResults, wvhtResults

def plotPercentAboveThreshold(jointResults: list, periodResults: list, wvhtResults: list, minPeriod: float, minWvht: float, stationID: str, showPlot: bool):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, periodResults, 'o-', color="darkorange", zorder=2, label="period filter")
    plt.plot(months, wvhtResults, 'o-', color="seagreen", zorder=2, label="wvht filter")
    plt.plot(months, jointResults, 'o-', color="royalblue", zorder=2, label="joint filter")
    plt.title(f'% of station {stationID} measurements above {minPeriod:.1f} s period and {minWvht:.1f} m wvht')
    plt.xlabel('Month')
    plt.ylabel('% above threshold')
    plt.ylim([-5, 105])
    plt.grid(zorder=1)
    plt.legend()

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_periodandwvhtthreshold.png', format='png')

def makePeriodWvhtFilterPlots(activeBOI: dict, nYearsBack: int, showPlots: bool, minPeriod: float, minWvht: float):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        joint, period, wvht = processHistoricalDataThroughFilter(thisBuoy.dataFrameHistorical, minPeriod, minWvht)
        print(f"met period and wvht threshold percentages = {[f'{x:.2f}' for x in joint]}")
        plotPercentAboveThreshold(joint, period, wvht, minPeriod, minWvht, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--minWvht", type=float, required=True, help="minimum wave height [m] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makePeriodWvhtFilterPlots(activeBOI, args.nYears, args.show, args.minPeriod, args.minWvht)

if __name__ == "__main__":
    main()

