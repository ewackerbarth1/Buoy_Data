import argparse
from ndbc_analysis_utilities.NDBCBuoy import NDBCBuoy
from ndbc_analysis_utilities.BuoyDataUtilities import getActiveBOI, calcDistanceBetweenNM, convertDistanceToSwellETA, calculateBearingAngle, estimateDensityTophatKernel, getNthPercentileSample, restricted_nDays_int, truncateAndReverse
from ndbc_analysis_utilities.PlottingUtilities import convertTimestampsToTimedeltas
import numpy as np
import matplotlib.pyplot as plt

def getXTicksForTimeDeltas(timeDeltas: np.ndarray[np.float64]) -> list[float]:
    minTimeDelta = min(timeDeltas)
    xTicks = []
    q, r = divmod(int(minTimeDelta), 24)
    nTicks = -1 * q
    if r == 0:
        nTicks += 1
        tickValue = q * 24
    else:
        tickValue = (q + 1) * 24

    for iTick in range(nTicks):
        xTicks.append(tickValue)
        tickValue += 24

    return xTicks

def getTimeSeriesData(buoy: NDBCBuoy, nDays: int) -> tuple:
    nSamples = buoy.convertRequestedDaysIntoSamples(nDays)
    dates = truncateAndReverse(buoy.dataFrameRealtime['Date'].to_numpy(), nSamples)
    waveheights = truncateAndReverse(buoy.dataFrameRealtime['WVHT'].to_numpy(), nSamples)
    sampleTimedeltas = convertTimestampsToTimedeltas(dates)
    return sampleTimedeltas, waveheights

def makeWvhtDistributionPlot(buoy: NDBCBuoy, nDays: int, bearingAngle: float, arrivalWindow: list, showPlots: bool):
    sampleTimedeltas, waveheights = getTimeSeriesData(buoy, nDays)

    rtSamplingVector, rtDist = estimateDensityTophatKernel(buoy.dataFrameRealtime['WVHT'].to_numpy(), 0.5)
    hSamplingVector, hDist = estimateDensityTophatKernel(buoy.dataFrameHistorical['WVHT'].to_numpy(), 0.5)

    fig = plt.figure(figsize=(13, 7))
    ax = fig.add_gridspec(top=0.95, right=0.75).subplots()
    ax2 = ax.inset_axes([1.05, 0, 0.25, 1], sharey=ax)

    def plotTimeSeries():
        h50thPercentileWvht = getNthPercentileSample(hSamplingVector, hDist, 50)
        h90thPercentileWvht = getNthPercentileSample(hSamplingVector, hDist, 90)
        print(f'50th percentile wvht for station {buoy.stationID} = {h50thPercentileWvht: 0.2f} m')
        print(f'90th percentile wvht for station {buoy.stationID} = {h90thPercentileWvht: 0.2f} m')

        xMin, xMax = min(sampleTimedeltas), max(sampleTimedeltas)
        print(f'min time delta = {xMin}, max time delta = {xMax}')

        ax.plot(sampleTimedeltas, waveheights, 'o-', color='royalblue', label='wvht', zorder=3)
        ax.hlines(h50thPercentileWvht, xMin, xMax, color='seagreen', ls=':', alpha=0.9, label='50th %', zorder=2)
        ax.hlines(h90thPercentileWvht, xMin, xMax, color='seagreen', ls='--', alpha=0.9, label='90th %', zorder=2)
        ax.set_ylabel('Wave height [m]')
        ax.set_xlabel('Sample time deltas [hrs]')
        ax.set_xticks(getXTicksForTimeDeltas(sampleTimedeltas))
        ax.legend()
        ax.set_title(f'Station {buoy.stationID} waveheights')
        ax.grid(zorder=0)
        ax.text(0.01, 0.95, f'Bearing angle to current loc = {bearingAngle: 0.1f} deg', transform=ax.transAxes, fontsize=10, zorder=1)
        ax.text(0.01, 0.92, f'Swell direction = {buoy.recentSwD: 0.1f} deg', transform=ax.transAxes, fontsize=10, zorder=1)

        # determine whether to plot arrival window
        if len(arrivalWindow) == 2:
            print(f'arrivalWindow = {arrivalWindow}')
            print(f'min time lag = {arrivalWindow[0]: 0.2f}hrs, max time lag = {arrivalWindow[1]: 0.2f}hrs')
            ax.fill_betweenx([min(waveheights), max(waveheights)], -1*arrivalWindow[1], -1*arrivalWindow[0], color='darkblue', alpha=0.4, label='currently arriving', zorder=1)

    def plotDistributions():
        ax2.fill_betweenx(rtSamplingVector, rtDist, 0, color='darkorange', alpha = 0.7, label='realtime', zorder=1)
        ax2.fill_betweenx(hSamplingVector, hDist, 0, color='seagreen', alpha = 0.7, label='historical', zorder=2)
        ax2.tick_params(axis='y', labelleft=False)
        ax2.legend(loc='upper left')
        xMin, xMax = ax2.get_xlim()
        ax2.set_xlim((xMax, xMin))
        ax2.set_xlabel('Density')
        ax2.grid(zorder=0)

    plotTimeSeries()
    plotDistributions()
    if showPlots:
        plt.show()
    else:
        plt.savefig(f'station_{buoy.stationID}_wvhtsdist.png', format='png')

def checkForArrivalWindow(swellDir: float, bearingAngle: float, distanceAway: float):
    # check if swell reaches station before current location
    # TODO: this is wrong right now!!!
    dDir = bearingAngle - swellDir
    if dDir > 180:
        dDir -= 360
    elif dDir < -180:
        dDir += 360

    arrivalWindow = []
    if abs(dDir) < 90:
        # calculate arrival window, TODO: calculate projected distance along the bearing angle line
        minSwellPeriod, maxSwellPeriod = 12, 18
        maxArrivalLag = convertDistanceToSwellETA(minSwellPeriod, distanceAway)
        minArrivalLag = convertDistanceToSwellETA(maxSwellPeriod, distanceAway)
        arrivalWindow = [minArrivalLag, maxArrivalLag]
        
    return arrivalWindow

def makeWVHTDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    currentLoc = (args.lat, args.lon)
    for stationID, stationLatLon in activeBOI.items():
        print(f'Instantiating NDBCBuoy {stationID}...')
        thisBuoy = NDBCBuoy(stationID)

        thisBuoy.fetchData(args.db)

        bearingAngle = calculateBearingAngle(stationLatLon, currentLoc)  # from buoy to current location in degrees
        arrivalWindow = checkForArrivalWindow(thisBuoy.recentSwD, bearingAngle, calcDistanceBetweenNM(currentLoc, stationLatLon))

        makeWvhtDistributionPlot(thisBuoy, args.nDays, bearingAngle, arrivalWindow, args.show)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")
    parser.add_argument("--nDays", type=restricted_nDays_int, required=True, help="# of recent days worth of data to plot (1-44), suggested is 1-4")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeWVHTDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()
