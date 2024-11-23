import duckdb


def connection(db_path="rstracer.db"):
    con = duckdb.connect(database=db_path, read_only=True)
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
