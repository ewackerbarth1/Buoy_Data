
## Example Usage

`python AnalyzingNDBCBuoyData.py --bf exampleBOI.txt --lat 32.96 --lon -117.23 --action display-map`

## MySQL Database

In order to minimize the number of requests made to the NDBC webpage, the analysis is configured to support writing to and reading from a MySQL database.
See the editDBTables.py file for the expected table structure and to intialize those tables. 
Reference the sampleconfig.py file for the variable expected in the database config file and make sure that you import the correct config file!

Once the database is configured, use the --db flag to interact with the database when running the analysis:

`python AnalyzingNDBCBuoyData.py --bf SDReducedBOI.txt --lat 32.96 --lon -117.23 --action display-map --db`

## Choosing Buoys of Interest

The ExampleBOI.txt file contains station ID's for a set of NDBC buoys. Navigate to the [NDBC webpage](https://www.ndbc.noaa.gov) and hover over station icons to get their ID's.
Then build your own BOI text file and point your analysis to it.

## Conda Package Manager

`conda env create -f CondaInstallEnvironment.yml`

## Example Visualizations

![close buoy](./sample_images/closebuoyexample.png)


![far buoy](./sample_images/fartherbuoyexample.png)


![buoy map](./sample_images/buoymapexample.png)

## Resources

- [NDBC home page](https://www.ndbc.noaa.gov)

- [NDBC Web Data Guide](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf)

- [Description of Buoy Data](https://www.ndbc.noaa.gov/measdes.shtml#stdmet)

