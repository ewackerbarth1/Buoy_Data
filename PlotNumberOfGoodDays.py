import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, getMonthlyDF
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def countGoodDays(df: pd.core.frame.DataFrame, minPeriod: float, minWvht: float) -> list:
    goodDaysPerMonth = [0] * 12
    filteredDF = df[(df['DPD'] >= minPeriod) & (df['WVHT'] >= minWvht)]
    print(f'Total # of good samples = {len(filteredDF)}')
    prevDay = -1 
    prevDate = None
    for idx, row in filteredDF.iterrows():
        thisDay = row['Date'].day
        if prevDay == -1 or thisDay != prevDay or row['Date'] - prevDate > pd.Timedelta(1, unit='d'):
            thisMonth = row['Date'].month
            goodDaysPerMonth[thisMonth - 1] += 1
        prevDay = thisDay
        prevDate = row['Date'] 

    print(f'Total # of good days = {sum(goodDaysPerMonth)}')
    return goodDaysPerMonth 

def plotNGoodDays(avgNGoodDays: list, minPeriod: float, minWvht: float, stationID: str, showPlot: bool):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, avgNGoodDays, 'o-', color="royalblue", zorder=2)
    plt.title(f'Avg # of good days / year (p > {minPeriod:.1f} s, wvht > {minWvht:.1f} m) at station {stationID}')
    plt.xlabel('Month')
    plt.ylabel('# of good days per year')
    plt.grid(zorder=1)

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_numgooddays.png', format='png')

def makeNGoodDaysPlots(activeBOI: dict, nYearsBack: int, showPlots: bool, minPeriod: float, minWvht: float):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        nGoodDaysPerMonth = countGoodDays(thisBuoy.dataFrameHistorical, minPeriod, minWvht)
        avgNGoodDays = [s / nYearsBack for s in nGoodDaysPerMonth]
        print(f"avg # of good days for each month = {[f'{x:.1f}' for x in avgNGoodDays]}")
        plotNGoodDays(avgNGoodDays, minPeriod, minWvht, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--minWvht", type=float, required=True, help="minimum wave height [m] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeNGoodDaysPlots(activeBOI, args.nYears, args.show, args.minPeriod, args.minWvht)

if __name__ == "__main__":
    main()


