import pymysql
import config

def startRDSConnection():
    # TODO: why am I using a DictCursor instead of a Cursor?
    try:
        connection = pymysql.connect(host=config.ENDPOINT,
                port=config.PORT,
                user=config.USERNAME,
                password=config.PASSWORD,
                database=config.DBNAME,
                cursorclass=pymysql.cursors.DictCursor,
                ssl_ca=config.SSL_CA
                )

        print('Successful RDS connection!')

    except Exception as e:
        print(f'RDS connection failed: {e}')
        connection = None

    return connection

def main():
    connection = startRDSConnection()
    if not connection:
        return
    
    connection.cursor().execute('''
        CREATE TABLE stations (
            id VARCHAR(255),
            location POINT
        )
    ''')

    connection.cursor().execute('''
        CREATE TABLE realtime_data (
            station_id VARCHAR(255),
            timestamp DATETIME,
            wvht FLOAT,
            swp FLOAT,
            swdir FLOAT
        )
    ''')

    connection.cursor().execute('''
        CREATE TABLE historical_data (
            station_id VARCHAR(255),
            timestamp DATETIME,
            wvht FLOAT,
            swp FLOAT,
            swdir FLOAT
        )
    ''')

    connection.commit()
    connection.close()

if __name__ == "__main__":
    main()


