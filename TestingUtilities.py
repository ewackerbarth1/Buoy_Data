# Testing Utilities

from BuoyDataUtilities import constructBuoyDict
from BuoyDataUtilities import findNearbyBuoys

buoysDict = constructBuoyDict()

print(len(buoysDict))
#help(constructBuoyDict)
#print(buoySoup)
#print(type(buoySoup))
#print(len(buoySoup))

sdLat = 32.72
sdLon = -117.16
dLat = 20
dLon = 20

nearbyBuoys = findNearbyBuoys(buoysDict, sdLat, sdLon, dLat, dLon)
