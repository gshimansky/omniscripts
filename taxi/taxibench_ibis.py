from braceexpand import braceexpand
import mysql.connector
import argparse
import time
import glob
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from server import OmnisciServer
from report import DbReport
from server_worker import OmnisciServerWorker


# Queries definitions
def q1(df):
    df.groupby('cab_type')[['cab_type']].count().execute()


def q2(df):
    df.groupby('passenger_count').aggregate(
        total_amount=df.total_amount.mean())[['passenger_count','total_amount']].execute()


def q3(df):
    df.groupby([df.passenger_count, df.pickup_datetime.year().name('pickup_datetime')]).aggregate(count=df.passenger_count.count()).execute()


def q4(df):
    df.groupby([df.passenger_count, df.pickup_datetime.year().name('pickup_datetime'),
                df.trip_distance]).size().sort_by([('pickup_datetime', True),
                                                   ('count', False)]).execute()


def timeq(q):
    t = time.time()
    q(df)
    return time.time()-t


def queries_exec(index):
    if index == 1:
        return timeq(q1)
    elif index == 2:
        return timeq(q2)
    elif index == 3:
        return timeq(q3)
    elif index == 4:
        return timeq(q4)
    else:
        print("Non-valid index value for queries function")
        sys.exit(3)
        return None


omnisci_executable = "../omnisci/build/bin/omnisci_server"
taxi_trips_directory = "/localdisk/work/trips_x*.csv"
taxibench_table_name = "trips"
omnisci_server = None

parser = argparse.ArgumentParser(description='Run NY Taxi benchmark using Ibis.')

parser.add_argument('-e', default=omnisci_executable, help='Path to executable "omnisci_server".')
parser.add_argument('-r', default="report_taxibench_ibis.csv", help="Report file name.")
parser.add_argument('-df', default=1, type=int,
                    help="Number of datafiles to input into database for processing.")
parser.add_argument('-dp', default=taxi_trips_directory,
                    help="Wildcard pattern of datafiles that should be loaded.")
parser.add_argument('-i', default=5, type=int,
                    help="Number of iterations to run every query. Best result is selected.")
parser.add_argument('-dnd', action='store_true',
                    help="Do not delete old table.")
parser.add_argument('-dni', action='store_true',
                    help="Do not create new table and import any data from CSV files.")
parser.add_argument("-port", default=62074, type=int,
                    help="TCP port that omnisql client should use to connect to server.")
parser.add_argument("-u", default="admin",
                    help="User name to use on omniscidb server.")
parser.add_argument("-p", default="HyperInteractive",
                    help="User password to use on omniscidb server.")
parser.add_argument("-n", default="agent_test_ibis",
                    help="Database name to use on omniscidb server.")
parser.add_argument("-db-server", default="localhost", help="Host name of MySQL server.")
parser.add_argument("-db-port", default=3306, type=int, help="Port number of MySQL server.")
parser.add_argument("-db-user", default="",
                    help="Username to use to connect to MySQL database. If user name is specified,\
                    script attempts to store results in MySQL database using other -db-parameters.")
parser.add_argument("-db-pass", default="omniscidb",
                    help="Password to use to connect to MySQL database.")
parser.add_argument("-db-name", default="omniscidb",
                    help="MySQL database to use to store benchmark results.")
parser.add_argument("-db-table", help="Table to use to store results for this benchmark.")

parser.add_argument("-commit_omnisci", dest="commit_omnisci",
                    default="1234567890123456789012345678901234567890",
                    help="Omnisci commit hash to use for tests.")
parser.add_argument("-commit_ibis", dest="commit_ibis",
                    default="1234567890123456789012345678901234567890",
                    help="Ibis commit hash to use for tests.")

try:
    args = parser.parse_args()
    if args.df <= 0:
        print("Bad number of data files specified", args.df)
        sys.exit(1)

    if args.i < 1:
        print("Bad number of iterations specified", args.i)

    database_name = args.n
    omnisci_server = OmnisciServer(omnisci_executable=args.e, omnisci_port=args.port,
                                   database_name=database_name, user=args.u,
                                   password=args.p)
    omnisci_server.launch()
    omnisci_server_worker = OmnisciServerWorker(omnisci_server)

    time.sleep(2)
    conn = omnisci_server_worker.connect_to_server()

    taxibench_columns_names = ["trip_id", "vendor_id", "pickup_datetime", "dropoff_datetime",
                               "store_and_fwd_flag", "rate_code_id", "pickup_longitude",
                               "pickup_latitude", "dropoff_longitude", "dropoff_latitude",
                               "passenger_count", "trip_distance", "fare_amount", "extra",
                               "mta_tax", "tip_amount", "tolls_amount", "ehail_fee",
                               "improvement_surcharge", "total_amount", "payment_type",
                               "trip_type", "pickup", "dropoff", "cab_type", "precipitation",
                               "snow_depth", "snowfall", "max_temperature", "min_temperature",
                               "average_wind_speed", "pickup_nyct2010_gid", "pickup_ctlabel",
                               "pickup_borocode", "pickup_boroname", "pickup_ct2010",
                               "pickup_boroct2010", "pickup_cdeligibil", "pickup_ntacode",
                               "pickup_ntaname", "pickup_puma", "dropoff_nyct2010_gid",
                               "dropoff_ctlabel", "dropoff_borocode", "dropoff_boroname",
                               "dropoff_ct2010", "dropoff_boroct2010", "dropoff_cdeligibil",
                               "dropoff_ntacode", "dropoff_ntaname", "dropoff_puma"]
    taxibench_columns_types = ['int32', 'string', 'timestamp', 'timestamp', 'string', 'int16',
                               'decimal', 'decimal', 'decimal', 'decimal', 'int16', 'decimal',
                               'decimal', 'decimal', 'decimal', 'decimal', 'decimal', 'decimal',
                               'decimal', 'decimal', 'string', 'int16', 'string', 'string',
                               'string', 'int16', 'int16', 'int16', 'int16', 'int16', 'int16',
                               'int16', 'string', 'int16', 'string', 'string', 'string', 'string',
                               'string', 'string', 'string', 'int16', 'string', 'int16', 'string',
                               'string', 'string', 'string', 'string', 'string', 'string']

    db_reporter = None
    if args.db_user is not "":
        print("Connecting to database")
        db = mysql.connector.connect(host=args.db_server, port=args.db_port, user=args.db_user,
                                     passwd=args.db_pass, db=args.db_name)
        db_reporter = DbReport(db, args.db_table, {
            'FilesNumber': 'INT UNSIGNED NOT NULL',
            'QueryName': 'VARCHAR(500) NOT NULL',
            'FirstExecTimeMS': 'BIGINT UNSIGNED',
            'WorstExecTimeMS': 'BIGINT UNSIGNED',
            'BestExecTimeMS': 'BIGINT UNSIGNED',
            'AverageExecTimeMS': 'BIGINT UNSIGNED',
            'TotalTimeMS': 'BIGINT UNSIGNED',
            'IbisCommitHash': 'VARCHAR(500) NOT NULL'
        }, {
            'ScriptName': 'taxibench_ibis.py',
            'CommitHash': args.commit_omnisci,
        })

    # Delete old table
    if not args.dnd:
        print("Deleting", database_name ,"old database")
        try:
            conn.drop_database(database_name, force=True)
            time.sleep(2)
            conn = omnisci_server_worker.connect_to_server()
        except Exception as err:
            print("Failed to delete", database_name, "old database: ", err)

    args.dp = args.dp.replace("'", "")
    data_files_names = list(braceexpand(args.dp))
    data_files_names = sorted([x for f in data_files_names for x in glob.glob(f)])
    data_files_number = len(data_files_names[:args.df])

    try:
        print("Creating", database_name ,"new database")
        conn.create_database(database_name) # Ibis list_databases method is not supported yet
    except Exception as err:
        print("Database creation is skipped, because of error:", err)

    if len(data_files_names) == 0:
        print("Could not find any data files matching", args.dp)
        sys.exit(2)

    # Create table and import data
    if not args.dni:
        # Datafiles import
        omnisci_server_worker.import_data(table_name=taxibench_table_name,
                                          data_files_names=data_files_names, files_limit=args.df,
                                          columns_names=taxibench_columns_names,
                                          columns_types=taxibench_columns_types, header=False)

    try:
        db = conn.database(database_name)
    except Exception as err:
        print("Failed to connect to database:", err)

    try:
        tables_names = db.list_tables()
        print("Database tables:", tables_names)
    except Exception as err:
        print("Failed to read database tables:", err)

    try:
        df = db.table(taxibench_table_name)
    except Exception as err:
        print("Failed to access", taxibench_table_name, "table:", err)

    try:
        with open(args.r, "w") as report:
            t_begin = time.time()
            for bench_number in range(1,5):
                exec_times = [None]*5
                best_exec_time = float("inf")
                worst_exec_time = 0.0
                first_exec_time = float("inf")
                times_sum = 0.0
                for iteration in range(1, args.i + 1):
                    print("RUNNING QUERY NUMBER", bench_number, "ITERATION NUMBER", iteration)
                    exec_times[iteration - 1] = int(round(queries_exec(bench_number) * 1000))
                    if iteration == 1:
                        first_exec_time = exec_times[iteration - 1]
                    if best_exec_time > exec_times[iteration - 1]:
                        best_exec_time = exec_times[iteration - 1]
                    if iteration != 1 and worst_exec_time < exec_times[iteration - 1]:
                        worst_exec_time = exec_times[iteration - 1]
                    if iteration != 1:
                        times_sum += exec_times[iteration - 1]
                average_exec_time = times_sum/(args.i - 1)
                total_exec_time = int(round((time.time() - t_begin)*1000))
                print("QUERY", bench_number, "EXEC TIME MS", best_exec_time,
                      "TOTAL TIME MS", total_exec_time)
                print("FilesNumber: ", data_files_number,  ",",
                      "IbisCommitHash", args.commit_ibis, ",",
                      "QueryName: ",  'Query' + str(bench_number), ",",
                      "FirstExecTimeMS: ", first_exec_time, ",",
                      "WorstExecTimeMS: ", worst_exec_time, ",",
                      "BestExecTimeMS: ", best_exec_time, ",",
                      "AverageExecTimeMS: ", average_exec_time, ",",
                      "TotalTimeMS: ", total_exec_time, ",",
                      "", '\n', file=report, sep='', end='', flush=True)
                if db_reporter is not None:
                    db_reporter.submit({
                        'FilesNumber': data_files_number,
                        'IbisCommitHash': args.commit_ibis,
                        'QueryName': 'Query' + str(bench_number),
                        'FirstExecTimeMS': first_exec_time,
                        'WorstExecTimeMS': worst_exec_time,
                        'BestExecTimeMS': best_exec_time,
                        'AverageExecTimeMS': average_exec_time,
                        'TotalTimeMS': total_exec_time
                    })
    except IOError as err:
        print("Failed writing report file", args.r, err)
except Exception as exc:
    print("Failed: ", exc)
finally:
    if omnisci_server:
        omnisci_server.terminate()