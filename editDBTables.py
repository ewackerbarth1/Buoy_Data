import pymysql
import config_local as config

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

def checkIfTableExists(connection, tableName) -> bool:
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES LIKE %s", (tableName,))
    nTablesLikeThis = cursor.rowcount
    cursor.close()

    if nTablesLikeThis > 0:
        return True
    else:
        return False

def createRealtimeDataTable(connection):
    connection.cursor().execute('''
        CREATE TABLE realtime_data (
            station_id VARCHAR(255),
            data MEDIUMTEXT
        )
    ''')

def deleteRealtimeDataTable(connection):
    connection.cursor().execute('DROP TABLE realtime_data')


def createHistoricalDataTable(connection):
    connection.cursor().execute('''
        CREATE TABLE historical_data (
            station_id VARCHAR(255),
            data MEDIUMTEXT
        )
    ''')

def deleteHistoricalDataTable(connection):
    connection.cursor().execute('DROP TABLE historical_data')

def createStationsTable(connection):
    connection.cursor().execute('''
        CREATE TABLE stations (
            id VARCHAR(255),
            location POINT
        )
    ''')

def main():
    connection = startRDSConnection()
    if not connection:
        return

    #createStationsTable(connection)
    #createRealtimeDataTable(connection)
    #createHistoricalDataTable(connection)

    #connection.commit()
    connection.close()

if __name__ == "__main__":
    main()


