import argparse
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, getMonthlyDF, getMonthName
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
from ndbc_analysis_utilities.HistoricalAnalysisUtilities import getCompleteHistoricalDataFrame
from ndbc_analysis_utilities.PlottingUtilities import makeCircularHist
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def getSwellDirs(df: pd.core.frame.DataFrame, minPeriod: float, minWvht: float) -> list[np.ndarray]:
    swellDirs = [] 
    for month in range(1, 13):
        monthDF = getMonthlyDF(df, month)
        goodSamples = monthDF[(monthDF['DPD'] >= minPeriod) & (monthDF['WVHT'] >= minWvht)]
        print(f'% of samples that passed filtering for {getMonthName(month)} = {len(goodSamples) / len(monthDF) * 100:.1f}%')
        swellDirs.append(goodSamples['MWD'].to_numpy())
    return swellDirs

def plotDirDists(swellDirs: list[np.ndarray], stationID: str, showPlot: bool, minPeriod: float, minWvht: float):
    swellDirsRad = [np.deg2rad(dirs) for dirs in swellDirs]

    nRows, nCols = 2, 6
    fig, ax = plt.subplots(nrows=nRows, ncols=nCols, figsize=(13, 6), subplot_kw=dict(projection='polar'))
    idx = 0
    for rIdx in range(nRows):
        for cIdx in range(nCols):
            makeCircularHist(ax[rIdx, cIdx], swellDirsRad[idx])
            ax[rIdx, cIdx].set_title(f'{getMonthName(idx+1)}')
            ax[rIdx, cIdx].grid(zorder=0)
            ax[rIdx, cIdx].set_theta_offset(np.pi / 2)
            ax[rIdx, cIdx].set_theta_direction(-1)
            ax[rIdx, cIdx].set_xticks(np.linspace(0, 2*np.pi, 8, endpoint=False))
            ax[rIdx, cIdx].set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
            ax[rIdx, cIdx].tick_params(axis='x', labelsize=7)
            for label in ax[rIdx, cIdx].get_xticklabels():
                label.set_position((label.get_position()[0], 0.1))
            idx += 1

    # TODO: text stating minWvht, minPeriod
    fig.suptitle(f"Station {stationID} swell directions")
    fig.subplots_adjust(left=0.04, right=0.96, bottom=0.02, top=0.9, hspace=0.1, wspace=0.4)
    if showPlot:
        plt.show()
    else:
        plt.savefig(f'station_{stationID}_swelldists_allmonths.png', format='png')

def makeDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    for stationID in activeBOI:
        historicalDF = getCompleteHistoricalDataFrame(NDBCBuoy(stationID), args.nYears)
        swellDirs = getSwellDirs(historicalDF, args.minPeriod, args.minWvht)
        plotDirDists(swellDirs, stationID, args.show, args.minPeriod, args.minWvht)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--nYears", type=int, required=True, help="# of years to include in historical data")
    parser.add_argument("--minPeriod", type=float, default=0.0, help="minimum swell period [s] for filtering historical data")
    parser.add_argument("--minWvht", type=float, default=0.0, help="minimum wave height [m] for filtering historical data")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()

