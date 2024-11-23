import duckdb

OUTPUT_PATH = ".output/rstracer"

TABLES = [
    "gold_dim_file_reg",
    "gold_dim_network_foreign_ip",
    "gold_dim_network_local_ip",
    "gold_dim_network_open_port",
    "gold_dim_network_socket",
    "gold_dim_network_host",
    "gold_dim_process",
    "gold_fact_file_reg",
    "gold_fact_network_ip",
    "gold_fact_network_packet",
    "gold_fact_process",
    "gold_fact_process_network",
    "gold_file_host",
    "gold_file_service",
    "gold_file_user",
    "gold_tech_chrono",
    "gold_tech_table_count",
]


def connection():
    con = duckdb.connect(database=":memory:")
    for table in TABLES:
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM '{OUTPUT_PATH}/{table}.parquet';")
    return con


class Process:

    def __init__(self, process_tuple):
        self.id = str(process_tuple[0])
        self.pid = process_tuple[1]
        self.ppid = process_tuple[2]
        self.user = process_tuple[3]
        self.full_command = process_tuple[4]
        self.started_at = process_tuple[5]


def get_descendants(con, pid):
    process_buffer = []

    def get_processes_by_ppid(ppids):  # todo
        process_buffer = []
        processes = con.execute(
            """
        SELECT
            HASH(pro.pid, started_at) AS _id,
            pro.pid,
            pro.ppid,
            usr.name AS user,
            pro.full_command,
            pro.started_at,
            pro.inserted_at,
        FROM gold_dim_process pro
        LEFT JOIN gold_file_user usr ON usr.uid = pro.uid
        WHERE pro.ppid IN ?""",
            [ppids],
        ).df()
        for row in processes.itertuples(index=False, name=None):
            process_buffer.append(Process(row))
        return process_buffer

    children = get_processes_by_ppid([pid])
    while len(children) > 0:
        process_buffer += children
        children = get_processes_by_ppid([child.pid for child in children])

    return process_buffer
