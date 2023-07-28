import argparse
from BuoyDataUtilities import getActiveBOI, getMonthlyDF, estimateDensityTophatKernel
from NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getPercentileSample(wvhts: np.ndarray, nthPercentile: int) -> np.float64:
    nSamples = len(wvhts)
    ithSample = int(np.ceil(nthPercentile / 100 * nSamples) - 1)
    sortedWvhts = np.sort(wvhts)
    return sortedWvhts[ithSample]

def getPeriodSamples(df: pd.core.frame.DataFrame, month: int, wvhtPercentile: float) -> np.ndarray:
    monthDF = getMonthlyDF(df, month)
    wvht = getPercentileSample(monthDF['WVHT'].to_numpy(), wvhtPercentile)
    metWvhtThreshold = monthDF[monthDF['WVHT'] >= wvht]
    print(f'Percentage of samples above {wvhtPercentile}th percentile = {len(metWvhtThreshold) / len(monthDF) * 100:.2f} %')
    return metWvhtThreshold['DPD'].to_numpy()

def plotPeriodDist(periodSamples: np.ndarray, stationID: str, showPlot: bool, minPeriod: float, wvhtPercentile: float, month: int):
    # text containing the percentage of samples above minPeriod top right
    periodSampleBinWidth = 1.0 
    samplesVector, periodDist = estimateDensityTophatKernel(periodSamples, periodSampleBinWidth)

    monthDict = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    fig, ax = plt.subplots()
    ax.fill_between(samplesVector, periodDist, color='seagreen', zorder=2)
    yMin, yMax = ax.get_ylim()
    ax.vlines(minPeriod, 0, yMax, color='black', ls=':', alpha=0.8, label=f'{minPeriod} s', zorder=3)
    ax.set_title(f'Station {stationID} period dist for samples above {wvhtPercentile}% wvht in {monthDict[month]}')
    ax.set_xlabel('swell period [s]')
    ax.set_ylabel('pdf')
    ax.grid(zorder=1)

    percentOfSamplesAboveMinPeriod = len(periodSamples[periodSamples >= minPeriod]) / len(periodSamples) * 100
    ax.text(0.6, 0.95, f'{percentOfSamplesAboveMinPeriod:.1f}% above {minPeriod} s period', transform=ax.transAxes, fontsize=8)

    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_periodDist.png', format='png')


def makePeriodDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    for stationID in activeBOI:
        thisBuoy = NDBCBuoy(stationID)
        thisBuoy.nYearsBack = args.nYears
        thisBuoy.nHistoricalMonths = 12
        thisBuoy.buildHistoricalDataFrame()

        periodSamples = getPeriodSamples(thisBuoy.dataFrameHistorical, args.month, args.wvhtPercentile)

        plotPeriodDist(periodSamples, stationID, args.show, args.minPeriod, args.wvhtPercentile, args.month)

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
    makePeriodDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()


