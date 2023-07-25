
## Conda Package Manager

`conda env create -f CondaInstallEnvironment.yml`

## Example Usage

`python AnalyzingNDBCBuoyData.py --bf ExampleBOI.txt --lat 32.96 --lon -117.23 --action display-map`

## Choosing Buoys of Interest

The ExampleBOI.txt file contains station ID's for a set of NDBC buoys. Navigate to the [NDBC webpage](https://www.ndbc.noaa.gov) and hover over station icons to get their ID's.
Then build your own BOI text file and point your analysis to it.

Note that there are different types of stations included on the NDBC map.
Some of them do not have realtime wave measurement capabilities.
In these cases, you will get an exception stating that there was a 404 status code.

## MySQL Database

In order to minimize the number of requests made to the NDBC webpage, the analysis is configured to support writing to and reading from a MySQL database.
See the editDBTables.py file for the expected table structure and to intialize those tables. 
Reference the sampleconfig.py file for the variable expected in the database config file and make sure that you import the correct config file!

Once the database is configured, we add data to it using the UpdateSwellDB.py script. We use the same script to update the real-time and historical data for our desired stations.
Here is an example call to UpdateSwellDB.py:

`python UpdateSwellDB.py --bf ExampleBOI.txt`

## Example Visualizations

![close buoy](./sample_images/closebuoyexample.png)


![far buoy](./sample_images/fartherbuoyexample.png)


![buoy map](./sample_images/buoymapexample.png)

## Resources

- [Project Google Doc](https://docs.google.com/document/d/1HXEw0J6tvZzVh7JCB2amuyUP60e3Qw9Z17ZvJnnqDZo/edit?usp=sharing)

- [NDBC home page](https://www.ndbc.noaa.gov)

- [NDBC Web Data Guide](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf)

- [Description of Buoy Data](https://www.ndbc.noaa.gov/measdes.shtml#stdmet)

