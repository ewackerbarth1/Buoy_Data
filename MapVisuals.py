# Work on map visualizations

import plotly.graph_objects as go
import pandas as pd
import numpy as np

from BuoyDataUtilities import constructBuoyDict
from BuoyDataUtilities import findNearbyBuoys
from BuoyDataUtilities import buoysDictToDF
from BuoyDataUtilities import collectBuoyData

# get buoys near San Diego
sdLat = 32.72
sdLon = -117.16
dLat = 1 
dLon = 1

# get active buoys nearby
buoysDict = constructBuoyDict()
nearbyBuoys = findNearbyBuoys(buoysDict, sdLat, sdLon, dLat, dLon)
nBuoys = len(nearbyBuoys)

# build data frame with lat and lon in separate columns
buoysDF = buoysDictToDF(nearbyBuoys)

# collect swell data from buoys
allBuoyData = collectBuoyData(nearbyBuoys)
print('# of rows = ', np.size(allBuoyData, axis=0))
print('# of columns = ', np.size(allBuoyData, axis=1))
print('Array height = ', np.size(allBuoyData, axis=2))

# save data
print(allBuoyData)


allBuoyDataNew = allBuoyData.reshape(allBuoyData.shape[0], -1)
print(allBuoyDataNew)
fName = 'SampleData/test1.txt'
np.savetxt(fName, allBuoyDataNew)

# make plots

# # create map centered at San Diego with nearby buoys plotted
# fig = go.Figure(go.Scattergeo())
# fig.update_geos(projection_type="natural earth",
#     showcoastlines = True,
#     showland = True,
#     showocean = True,
#     showlakes = True,
#     center = dict(lon=sdLon, lat=sdLat),
#     lataxis_range=[sdLat-dLat, sdLat+dLat],
#     lonaxis_range=[sdLon-dLon, sdLon+dLon])
# fig.add_trace(go.Scattergeo(lon = [sdLon], lat = [sdLat],
#     mode = 'markers',
#     name = 'San Diego',
#     marker = dict(
#         color = 'rgb(0, 0, 255)',
#         symbol = 'x'
#         )
#     ))
# fig.add_trace(go.Scattergeo(lon = buoysDF['lon'], lat = buoysDF['lat'],
#     mode = 'markers',
#     name = 'buoys',
#     marker = dict(
#         color = 'rgb(255, 0, 0)')
#     ))
# fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})
# fig.show()
# 

# make scatter plot 
