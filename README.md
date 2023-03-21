
## Example Usage

python AnalyzingNDBCBuoyData.py --bf SDReducedBOI.txt --lat 32.96 --lon -117.23 --action display-map

## MySQL Database

In order to minimize the number of requests made to the NDBC webpage, the analysis is configured to support writing to and reading from a MySQL database.
See the editDBTables.py file for the expected table structure.
To avoid using a database, set the --db flag to false when running AnalyzingNDBCBuoyData.py.

## Conda Package Manager

conda env create -f CondaInstallEnvironment.yml

## Example Visualizations

![close buoy](./sample_images/closebuoyexample.png)


![far buoy](./sample_images/fartherbuoyexample.png)


![buoy map](./sample_images/buoymapexample.png)

## Resources
NDBC Web Data Guide at:
https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf

Description of Buoy Data at:
https://www.ndbc.noaa.gov/measdes.shtml#stdmet

