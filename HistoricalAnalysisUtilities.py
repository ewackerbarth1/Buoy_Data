from NDBCBuoy import NDBCBuoy
import pandas as pd

def getCompleteHistoricalDataFrame(buoy: NDBCBuoy, nYears: int) -> pd.core.frame.DataFrame:
    buoy.nYearsBack = nYears
    buoy.nHistoricalMonths = 12
    buoy.buildHistoricalDataFrame()
    return buoy.dataFrameHistorical
