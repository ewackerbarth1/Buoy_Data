import argparse
from BuoyDataUtilities import getActiveBOI, getMonthlyDF, getMonthName, makeCircularHist
from NDBCBuoy import NDBCBuoy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from HistoricalAnalysisUtilities import getCompleteHistoricalDataFrame

def getSwellDirs(df: pd.core.frame.DataFrame, month: int, minPeriod: float, minWvht: float) -> np.ndarray:
    monthDF = getMonthlyDF(df, month)
    goodSamples = monthDF[(monthDF['DPD'] >= minPeriod) & (monthDF['WVHT'] >= minWvht)]
    print(f'% of samples that passed filtering = {len(goodSamples) / len(monthDF) * 100:.1f}%')
    swellDirs = goodSamples['MWD'].to_numpy()
    return swellDirs

def plotDirDistribution(swellDirs: np.ndarray, stationID: str, month: int, showPlot: bool, minPeriod: float, minWvht: float):
    swellDirsRad = np.deg2rad(swellDirs) 

    fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
    makeCircularHist(ax, swellDirsRad)
    ax.set_title(f'Station {stationID} swell direction dist for {getMonthName(month)}')
    ax.grid(zorder=0)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(np.linspace(0, 2*np.pi, 8, endpoint=False))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])

    # TODO: text stating minWvht, minPeriod
    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_swelldist_{getMonthName(month)}.png', format='png')

def makeDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    for stationID in activeBOI:
        historicalDF = getCompleteHistoricalDataFrame(NDBCBuoy(stationID), args.nYears)
        swellDirs = getSwellDirs(historicalDF, args.month, args.minPeriod, args.minWvht)
        plotDirDistribution(swellDirs, stationID, args.month, args.show, args.minPeriod, args.minWvht)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, default=0.0, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--minWvht", type=float, default=0.0, help="minimum wave height [m] for filtering historical data")
    parser.add_argument("--month", type=int, required=True, help="month to look at (1-12)")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()
