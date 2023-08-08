import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, getMonthlyDF, getMonthName, getNthPercentileSampleWithoutPMF
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import datetime

def calcNGoodDays(dates: pd.core.series.Series) -> int:
    uniqueDays = set(dates.dt.day)
    return len(uniqueDays) 

def getNGoodDaysPerYear(df: pd.core.frame.DataFrame, years: list[int], month: int, minPeriod: float, wvhtPercentile: float) -> list[int]:
    monthDF = getMonthlyDF(df, month)
    goodWvht = getNthPercentileSampleWithoutPMF(monthDF['WVHT'].to_numpy(), wvhtPercentile)
    goodDaySamples = monthDF[(monthDF['WVHT'] >= goodWvht) & (monthDF['DPD'] >= minPeriod)]
    print(f'percentage of good day samples = {len(goodDaySamples) / len(monthDF) * 100:.2f}')
    nGoodDaysPerYear = []
    for y in years:
        goodDaySamplesForThisYear = goodDaySamples[goodDaySamples['Date'].dt.year == y]
        nGoodDaysPerYear.append(calcNGoodDays(goodDaySamplesForThisYear['Date']))

    return nGoodDaysPerYear

def plotGoodDaysPerYear(nGoodDays: list, years: list, stationID: str, showPlot: bool, minPeriod: float, wvhtPercentile: float, month: int):
    fig, ax = plt.subplots()
    ax.plot(years, nGoodDays, 'o-', color='royalblue', zorder=2)
    ax.set_title(f'Station {stationID} good days per year in {getMonthName(month)}')
    ax.set_xlabel('Year')
    ax.set_ylabel('# of good days')
    ax.grid(zorder=1)
    ax.text(0.55, 0.95, f'period >= {minPeriod} s and wvht >= {wvhtPercentile}th %', transform=ax.transAxes, fontsize=8, zorder=2)
    ax.set_xticks(years)
    ax.set_ylim([-0.5, ax.get_ylim()[1]])

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_NGoodDaysPerYear.png', format='png')


def makeNGoodDaysPlots(activeBOI: dict, args: argparse.Namespace):
    thisYear = datetime.datetime.now().year
    years = list(range(thisYear - args.nYears, thisYear))
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = args.nYears
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        nGoodDays = getNGoodDaysPerYear(thisBuoy.dataFrameHistorical, years, args.month, args.minPeriod, args.wvhtPercentile)

        plotGoodDaysPerYear(nGoodDays, years, stationID, args.show, args.minPeriod, args.wvhtPercentile, args.month)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--wvhtPercentile", type=float, required=True, help="selected measurements need to have wvht measurements at or above this percentile")
    parser.add_argument("--month", type=int, required=True, help="month to look at (1-12)")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeNGoodDaysPlots(activeBOI, args)

if __name__ == "__main__":
    main()



