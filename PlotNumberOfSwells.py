import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, getMonthlyDF
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def analyzeSwells(df: pd.core.frame.DataFrame, minPeriod: float, minWvht: float) -> list:
    nAllowedMissedSamples = 4
    swellsPerMonth = [0] * 12
    filteredDF = df[(df['DPD'] >= minPeriod) & (df['WVHT'] >= minWvht)]
    #print('filtered DF:')
    #print(filteredDF)
    print(f'Total # of swell samples = {len(filteredDF)}')
    prevIdx = -1 
    for idx, row in filteredDF.iterrows():
        if prevIdx == -1 or idx - prevIdx > nAllowedMissedSamples + 1:
            thisMonth = row['Date'].month
            swellsPerMonth[thisMonth - 1] += 1
        prevIdx = idx

    print(f'Total # of swells = {sum(swellsPerMonth)}')
    return swellsPerMonth

def plotAvgSwellsPerMonth(avgSwellsPerMonth: list, minPeriod: float, minWvht: float, stationID: str, showPlot: bool):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    plt.plot(months, avgSwellsPerMonth, 'o-', color="royalblue", zorder=2)
    plt.title(f'Avg # of swells (period > {minPeriod:.1f} s, wvht > {minWvht:.1f} m) per year at station {stationID}')
    plt.xlabel('Month')
    plt.ylabel('# of swells per year')
    plt.grid(zorder=1)

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_numswells.png', format='png')

def makeAvgSwellsPlots(activeBOI: dict, nYearsBack: int, showPlots: bool, minPeriod: float, minWvht: float):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = nYearsBack
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        nSwellsPerMonth = analyzeSwells(thisBuoy.dataFrameHistorical, minPeriod, minWvht)
        avgSwellsPerMonth = [s / nYearsBack for s in nSwellsPerMonth]
        print(f"avg # of swells for each month = {[f'{x:.1f}' for x in avgSwellsPerMonth]}")
        plotAvgSwellsPerMonth(avgSwellsPerMonth, minPeriod, minWvht, stationID, showPlots)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, required=True, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--minWvht", type=float, required=True, help="minimum wave height [m] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeAvgSwellsPlots(activeBOI, args.nYears, args.show, args.minPeriod, args.minWvht)

if __name__ == "__main__":
    main()


