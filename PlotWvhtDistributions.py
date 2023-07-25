import argparse
from NDBCBuoy import NDBCBuoy
from BuoyDataUtilities import getActiveBOI, calcDistanceBetweenNM, convertDistanceToSwellETA, calculateBearingAngle, estimateDensityTophatKernel, getNthPercentileSample
import numpy as np
import matplotlib.pyplot as plt

def makeWVHTDistributionPlots(activeBOI: dict, args: argparse.Namespace):
    nDaysToInclude = 4
    minSwellPeriod, maxSwellPeriod = 12, 18
    currentLoc = (args.lat, args.lon)
    for stationID, stationLatLon in activeBOI.items():
        print(f'Instantiating NDBCBuoy {stationID}...')
        thisBuoy = NDBCBuoy(stationID)

        if args.db:
            fetchSuccess = thisBuoy.fetchDataFromDB()
            if not fetchSuccess:
                print(f'Unable to fetch data for station {stationID} from database')
                continue
        else:
            thisBuoy.setLocation(stationLatLon)
            thisBuoy.fetchDataFromNDBCPage()

        thisBuoy.buildAnalysisProducts()

        # set arrival window
        distanceAway = calcDistanceBetweenNM(currentLoc, stationLatLon)
        maxArrivalLag = convertDistanceToSwellETA(minSwellPeriod, distanceAway)
        minArrivalLag = convertDistanceToSwellETA(maxSwellPeriod, distanceAway)
        thisBuoy.setArrivalWindow((minArrivalLag, maxArrivalLag))

        bearingAngle = calculateBearingAngle(stationLatLon, currentLoc)  # from buoy to current location in degrees
        makeWvhtDistributionPlot(thisBuoy, nDaysToInclude, bearingAngle, args.show)

def convertTimestampsToTimedeltas(timestamps: np.ndarray[np.datetime64]) -> np.ndarray[np.float64]:
    now = np.datetime64('now')
    deltas = now - timestamps
    deltaMins = deltas.astype('timedelta64[m]')
    deltaHrs = -1 * deltaMins.astype('float') / 60
    return deltaHrs 

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

def makeWvhtDistributionPlot(buoy: NDBCBuoy, nDays: int, bearingAngle: float, showPlots: bool):
    nSamples = buoy.convertRequestedDaysIntoSamples(nDays)
    #print(f'nSamples = {nSamples}')
    waveheights, sampleDates = buoy.getOrientedWvhtsAndDates(nSamples)
    sampleTimedeltas = convertTimestampsToTimedeltas(sampleDates)

    rtSamplingVector, rtDist = estimateDensityTophatKernel(buoy.dataFrameRealtime['WVHT'].to_numpy(), 0.5)
    hSamplingVector, hDist = estimateDensityTophatKernel(buoy.dataFrameHistorical['WVHT'].to_numpy(), 0.5)

    h50thPercentileWvht = getNthPercentileSample(hSamplingVector, hDist, 50)
    h90thPercentileWvht = getNthPercentileSample(hSamplingVector, hDist, 90)
    print(f'50th percentile wvht for station {buoy.stationID} = {h50thPercentileWvht: 0.2f} m')
    print(f'90th percentile wvht for station {buoy.stationID} = {h90thPercentileWvht: 0.2f} m')

    print(f'min time lag = {buoy.arrivalWindow[0]: 0.2f}hrs, max time lag = {buoy.arrivalWindow[1]: 0.2f}hrs')
    arrivalWindow = [-1 * x for x in buoy.arrivalWindow]

    xMin, xMax = min(sampleTimedeltas), max(sampleTimedeltas)
    print(f'min time delta = {xMin}, max time delta = {xMax}')

    fig = plt.figure(figsize=(13, 7))
    ax = fig.add_gridspec(top=0.95, right=0.75).subplots()
    ax2 = ax.inset_axes([1.05, 0, 0.25, 1], sharey=ax)

    def plotTimeSeries():
        ax.plot(sampleTimedeltas, waveheights, 'o-', color='royalblue', label='wvht')
        ax.hlines(h50thPercentileWvht, xMin, xMax, color='seagreen', ls=':', alpha=0.9, label='50th %')
        ax.hlines(h90thPercentileWvht, xMin, xMax, color='seagreen', ls='--', alpha=0.9, label='90th %')
        ax.fill_betweenx([min(waveheights), max(waveheights)], arrivalWindow[1], arrivalWindow[0], color='darkblue', alpha=0.4, label='currently arriving')
        ax.set_ylabel('Wave height [m]')
        ax.set_xlabel('Sample time deltas [hrs]')
        ax.set_xticks(getXTicksForTimeDeltas(sampleTimedeltas))
        #ax.tick_params(axis='x', labelrotation=45, labelsize=7)
        ax.legend()
        ax.set_title(f'Station {buoy.stationID} waveheights')
        ax.grid()
        ax.text(0.01, 0.95, f'Bearing angle to current loc = {bearingAngle: 0.1f} deg', transform=ax.transAxes, fontsize=10)
        ax.text(0.01, 0.92, f'Swell direction = {buoy.recentSwD: 0.1f} deg', transform=ax.transAxes, fontsize=10)

    def plotDistributions():
        #ax2.plot(rtDist, rtSamplingVector, color='darkorange', label='realtime')
        #ax2.plot(hDist, hSamplingVector, color='seagreen', label='historical')
        ax2.fill_betweenx(rtSamplingVector, rtDist, 0, color='darkorange', alpha = 0.7, label='realtime')
        ax2.fill_betweenx(hSamplingVector, hDist, 0, color='seagreen', alpha = 0.7, label='historical')
        ax2.tick_params(axis='y', labelleft=False)
        ax2.legend(loc='upper left')
        xMin, xMax = ax2.get_xlim()
        ax2.set_xlim((xMax, xMin))
        ax2.set_xlabel('Density')
        ax2.grid()

    plotTimeSeries()
    plotDistributions()
    #manager = plt.get_current_fig_manager()
    #manager.full_screen_toggle()
    if showPlots:
        plt.show()
    else:
        plt.savefig(f'station_{buoy.stationID}.png', format='png')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")
    parser.add_argument("--show", action='store_true', help="use this flag if you want to display the figures instead of saving them")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    makeWVHTDistributionPlots(activeBOI, args)

if __name__ == "__main__":
    main()
