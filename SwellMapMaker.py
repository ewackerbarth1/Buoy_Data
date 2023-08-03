import pandas as pd
import numpy as np
import plotly.graph_objects as go
import argparse

from NDBCBuoy import NDBCBuoy
from BuoyDataUtilities import calcDistanceBetweenNM, getActiveBOI, convertSwellETAToDistance, convertDegreesToRadians, convertMetersToNM

class SwellMapMaker():
    def __init__(self, currentLoc: tuple, useDB=True):
        self.currentLoc = currentLoc
        self.useDB = useDB

    def buildBOIDF(self, activeBOI: dict):
        boiData = []
        for stationID, stationLatLon in activeBOI.items():
            print(f'Instantiating NDBCBuoy {stationID}...')
            thisBuoy = NDBCBuoy(stationID)
            
            thisBuoy.fetchData(self.useDB)

            thisBuoy.setWVHTPercentileHistorical()
            thisBuoy.setWVHTPercentileRealtime()
            distanceAway = calcDistanceBetweenNM(self.currentLoc, stationLatLon)
            buoyInfo = [stationID, stationLatLon[0], stationLatLon[1], distanceAway]
            buoyReadings = [thisBuoy.recentWVHT, thisBuoy.recentSwP, thisBuoy.recentSwD, thisBuoy.wvhtPercentileRealtime, thisBuoy.wvhtPercentileHistorical]
            hoverText = [f'{stationID}, wvht [m, %rt, %hi]: {thisBuoy.recentWVHT:0.1f}m / {thisBuoy.wvhtPercentileRealtime:0.0f}% / {thisBuoy.wvhtPercentileHistorical:0.0f}%, swp [s]: {thisBuoy.recentSwP}'] #{distanceAway:0.2f} NM away'
            thisBuoyData = buoyInfo + buoyReadings + hoverText
            boiData.append(thisBuoyData)

        self.buoysDF = pd.DataFrame(boiData, columns=['ID', 'lat', 'lon', 'distanceAway', 'wvht', 'swp', 'swd', 'wvhtPercentileRealtime', 'wvhtPercentileHistorical', 'hoverText'])
        print('Buoys dataframe:')
        print(self.buoysDF)

    def mapBuoys(self):
        fig = go.Figure(go.Scattergeo())

        fig.update_geos(projection_type="orthographic",
                showcoastlines = True,
                showland = True,
                showocean = True,
                showlakes = True,
                resolution = 50, 
                fitbounds = 'locations'
                )

        self.plotRangeBands(fig)
        self.plotSwellDirection(fig)
        self.plotWaveheightAndPeriodMarkers(fig)

        self.addWvhtsToLegend(fig)
        self.addSwpToLegend(fig)
        self.addSwdToLegend(fig)

        self.plotCurrentLocation(fig)

        fig.update_layout(showlegend=True, height=600, margin={"r":0,"t":0,"l":0,"b":0})
        fig.update_layout(legend=dict(
            yanchor="top",
            xanchor="left",
            y=0.99,
            x=0.01,
            font = dict(
                size = 16)
            ))

        fig.show()

    def generateConstantDistancePoints(self, bearings, distanceAwayNM, lat1Deg, lon1Deg):
        earthRadius = 6371e3   # meters

        lat1, lon1 = convertDegreesToRadians(lat1Deg), convertDegreesToRadians(lon1Deg)
        d = distanceAwayNM / convertMetersToNM(earthRadius)

        lats = np.arcsin(np.sin(lat1) * np.cos(d) + np.cos(lat1) * np.sin(d) * np.cos(bearings))
        lons = lon1 + np.arctan2(np.sin(bearings) * np.sin(d) * np.cos(lat1), np.cos(d) - np.sin(lat1) * np.sin(lats))

        lats *= 180 / np.pi
        lons *= 180 / np.pi
        return lats, lons

    def plotRangeCircles(self, fig):
        nSamplesPerCircle = 100
        hoursAway = [4, 12, 24, 48]
        prototypeSwellPeriodInSeconds = 15  
        bearings = np.linspace(0, 2*np.pi, nSamplesPerCircle)
        for swellEta in hoursAway:
            distanceAwayNM = convertSwellETAToDistance(prototypeSwellPeriodInSeconds, swellEta)
            lats, lons = self.generateConstantDistancePoints(bearings, distanceAwayNM, self.currentLoc[0], self.currentLoc[1])

            fig.add_trace(go.Scattergeo(
                lon = lons,
                lat = lats,
                mode = 'lines',
                name = f'+{swellEta} hrs',
                hoverinfo = 'name',
                opacity = 0.5,
                marker = dict(
                    color = 'rgb(0, 0, 0)'
                    )
                )
                )

    def plotRangeBands(self, fig):
        nSamplesPerCircle = 100
        hoursAway = [4, 12, 24, 48]
        prototypeSwellPeriodInSeconds = 15  
        minSwellPeriod = 12
        maxSwellPeriod = 18
        bearings = np.linspace(0, 2*np.pi, nSamplesPerCircle)
        #bearings = np.concatenate((bearings, np.array([0])))
        #print(f'bearings = {bearings}')
        for swellEta in hoursAway:
            maxDistanceAwayNM = convertSwellETAToDistance(maxSwellPeriod, swellEta)
            minDistanceAwayNM = convertSwellETAToDistance(minSwellPeriod, swellEta)
            latsMin, lonsMin = self.generateConstantDistancePoints(bearings, minDistanceAwayNM, self.currentLoc[0], self.currentLoc[1])
            latsMax, lonsMax = self.generateConstantDistancePoints(bearings, maxDistanceAwayNM, self.currentLoc[0], self.currentLoc[1])

            lats = np.concatenate((latsMax, latsMin[::-1]))
            lons = np.concatenate((lonsMax, lonsMin[::-1]))
            #print(f'lats = {lats}')
            #print(f'lons = {lons}')

            fig.add_trace(go.Scattergeo(
                lon = lons,
                lat = lats,
                mode = 'lines',
                name = f'+{swellEta} hrs',
                hoverinfo = 'none',
                fillcolor = 'rgba(0, 128, 128, 0.1)',
                fill = 'toself',
                showlegend = False,
                line = dict(
                    width = 0
                    )
                )
                )

            latsTriangle = np.array([latsMax[0], latsMin[1], latsMin[0], latsMax[0]])
            lonsTriangle = np.array([lonsMax[0], lonsMin[1], lonsMin[0], lonsMax[0]])

            fig.add_trace(go.Scattergeo(
                lon = lonsTriangle,
                lat = latsTriangle,
                mode = 'lines',
                fill = 'toself',
                fillcolor = 'rgba(0, 128, 128, 0.1)',
                showlegend = False,
                hoverinfo = 'none',
                line = dict(
                    width = 0
                    )
                )
                )

            avgLat = np.mean(latsTriangle)
            avgLon = np.mean(lonsTriangle)

            fig.add_trace(go.Scattergeo(
                lon = [avgLon],
                lat = [avgLat],
                mode = 'lines+text',
                showlegend = False,
                text = f'+{swellEta} hrs',
                textposition = 'bottom center',
                hoverinfo = 'none',
                line = dict(
                    width = 0
                    )
                )
                )

    def calculateMarkerSizes(self, wvhtPercentiles):
        minMarkerSize = 6 
        markerSizes = wvhtPercentiles // 10 + minMarkerSize 
        return markerSizes

    def getMarkerColors(self, swp):
        greenGEQ = 15
        redLEQ = 10

        greenRGB = 'rgb(0, 255, 0)'
        yellowRGB = 'rgb(255, 255, 0)'
        redRGB = 'rgb(255, 0, 0)'

        markerColors = []
        for p in swp:
            if p >= greenGEQ:
                markerColors.append(greenRGB)
            elif p <= redLEQ:
                markerColors.append(redRGB)
            else:
                markerColors.append(yellowRGB)

        return markerColors

    def plotWaveheightAndPeriodMarkers(self, fig):
        markerSizes = self.calculateMarkerSizes(self.buoysDF['wvhtPercentileHistorical'].to_numpy())
        markerColors = self.getMarkerColors(self.buoysDF['swp'].to_numpy())

        fig.add_trace(go.Scattergeo(
            lon = self.buoysDF['lon'],
            lat = self.buoysDF['lat'],
            text = self.buoysDF['hoverText'],
            mode = 'markers',
            name = 'buoys',
            hoverinfo = 'lat+lon+text',
            showlegend = False,
            marker = dict(
                color = markerColors,
                symbol = 'circle',
                size = markerSizes 
                )
            )
            )

    def buildArrow(self):
        widthScale = 0.5
        lengthScale = 1
        x = [-0.5, -0.5, -1, 0, 1, 0.5, 0.5, -0.5]
        y = [-1, 1, 1, 2, 1, 1, -1, -1]
        arrow = np.array([x, y])
        arrow[0, :] = widthScale * arrow[0, :]
        arrow[1, :] = lengthScale * arrow[1, :]
        #print(f'Arrow has shape {arrow.shape}')
        return arrow 

    def rotateArrowCW(self, arrow, theta: float):
        R = np.array([[np.cos(theta), np.sin(theta)], [-1*np.sin(theta), np.cos(theta)]])
        #print(f'shape of R = {R.shape}')
        #print(f'shape of arrow = {arrow.shape}')
        return R @ arrow

    def scaleArrow(self, arrow, scaleFactor: float):
        return scaleFactor * arrow

    def translateArrow(self, arrow, lat, lon):
        nRows, nCols = arrow.shape
        #print(f'# of rows = {nRows}, # of cols = {nCols}')
        return arrow + np.array([lon*np.ones(nCols), lat*np.ones(nCols)])

    def plotSwellDirection(self, fig):
        prototypeArrow = self.buildArrow()
        swellDirs = self.buoysDF['swd'].to_numpy()
        for buoyIdx, thisDir in enumerate(swellDirs):
            thisArrow = self.rotateArrowCW(prototypeArrow, thisDir * np.pi / 180)
            thisArrow = self.scaleArrow(thisArrow, 0.5)
            buoyLat = self.buoysDF['lat'].iloc[buoyIdx]
            buoyLon = self.buoysDF['lon'].iloc[buoyIdx]
            thisArrow = self.translateArrow(thisArrow, buoyLat, buoyLon)

            fig.add_trace(go.Scattergeo(
                lon = thisArrow[0, :],
                lat = thisArrow[1, :],
                text = f'{thisDir} deg',
                mode = 'lines',
                fill = 'toself',
                hoverinfo = 'none',
                fillcolor = 'rgba(0, 0, 128, 0.7)',
                showlegend = False,
                line = dict(
                    width = 0
                    )
                )
                )

    def plotCurrentLocation(self, fig):
        # current location marker
        fig.add_trace(go.Scattergeo(lon = [self.currentLoc[1]], lat = [self.currentLoc[0]],
            mode = 'markers',
            name = 'Current Location',
            showlegend = True,
            marker = dict(
                color = 'rgb(0, 0, 0)',
                symbol = 'x',
                size = 12
                )
            ))

    def addWvhtsToLegend(self, fig):
        wvhtsToAddToLegend = [10, 50, 90]
        for thisWvht in wvhtsToAddToLegend:
            fig.add_trace(go.Scattergeo(
                lat = [self.currentLoc[0]],
                lon = [self.currentLoc[1]],
                name = f'{thisWvht}th % wvht',
                mode = 'markers',
                visible = 'legendonly',
                marker = dict(
                    color = 'rgb(0, 0, 0)',
                    symbol = 'circle',
                    size = self.calculateMarkerSizes(thisWvht)
                    )
                )
                )

    def addSwpToLegend(self, fig):
        swpToAddToLegend = [10, 13, 15]
        names = ['period <= 10s', '10s < period < 15s', 'period >=15s']
        for idx, thisSwp in enumerate(swpToAddToLegend):
            fig.add_trace(go.Scattergeo(
                lat = [self.currentLoc[0]],
                lon = [self.currentLoc[1]],
                name = names[idx],
                mode = 'markers',
                visible = 'legendonly',
                marker = dict(
                    color = self.getMarkerColors([thisSwp]),
                    symbol = 'circle',
                    size = self.calculateMarkerSizes(50)
                    )
                )
                )

    def addSwdToLegend(self, fig):
        fig.add_trace(go.Scattergeo( 
            lat = [self.currentLoc[0]],
            lon = [self.currentLoc[1]],
            name = 'swell direction',
            mode = 'markers',
            visible = 'legendonly',
            marker = dict(
                color = 'rgb(0, 0, 128)',
                symbol = 'arrow-up',
                size = 10 
                )
            )
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="longitude in degrees")
    parser.add_argument("--bf", type=str, required=True, help="text file name containing buoys of interest")
    parser.add_argument("--db", action='store_true', help="use this flag if you are using a MySQL db instance")

    args = parser.parse_args()

    activeBOI = getActiveBOI(args.bf)
    currentLoc = (args.lat, args.lon)
    mapMaker = SwellMapMaker(currentLoc, args.db)
    mapMaker.buildBOIDF(activeBOI)
    mapMaker.mapBuoys()

if __name__ == "__main__":
    main()

