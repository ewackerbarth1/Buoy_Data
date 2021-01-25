# Initial_Data_Request is our first attempt to collect time series data
# from the NDBC and produce some plots
#

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import matplotlib.pyplot as plt

# build url for buoy data
buoyID = '46047'
baseURL = 'https://www.ndbc.noaa.gov/data/realtime2/'
buoyURL = baseURL + buoyID + '.spec'
#buoyURL = 'https://www.ndbc.noaa.gov/data/realtime2/46047.spec'

# ------------------------ webpage contents --------------------------------

# get webpage
ndbcPage = requests.get(buoyURL)       #<class 'requests.models.Response'>

# parse the webpage
buoySoup = BeautifulSoup(ndbcPage.content, 'html.parser') #<class 'bs4.BeautifulSoup'>

# --------------------------- soup --> dataFrame ------------------------------

# convert soup to a string
soupString = str(buoySoup)

# split string based on row divisions
rowList = re.split("\n+", soupString)

# @2do: remove last entry if necessary
rowList = rowList[:-1]

# split rows into individual entries using spaces
entryList = [re.split(" +", iRow) for iRow in rowList]

# build data frame
dFrame1 = pd.DataFrame(entryList[2:], columns = entryList[0])  # ignore first 2 rows

# add 'samples' column that goes from 1 to the number of rows in data frame
dfSize = dFrame1.shape # 2 element tuple (nRows, nColumns)
nRows = dfSize[0]
samplesList = list(range(nRows, 0, -1))   #1082:-1:1
dFrame1['Samples'] = samplesList

print(dFrame1)

# change types of dataFrame columns
dFrame1["WVHT"] = pd.to_numeric(dFrame1["WVHT"])
dFrame1["SwP"] = pd.to_numeric(dFrame1["SwP"])

# ---------------------- plot some stuff -------------------------------

# wave height
dFrame1.plot(x='Samples', y='WVHT', kind='line', marker='o')
plt.title('Wave height')
plt.xlabel('Samples')
plt.ylabel('Height [m]')
plt.grid(True)
plt.show()

# swell period
dFrame1.plot(x='Samples', y='SwP', kind='line', marker='o')
plt.title('Swell period')
plt.xlabel('Samples')
plt.ylabel('Period [s]')
plt.grid(True)
plt.show()
