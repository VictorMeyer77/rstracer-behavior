import os
from datetime import datetime
from timeit import default_timer as timer

import streamlit as st

from pages import connection, get_descendants

start_timer = timer()
con = connection()
analyse_start = datetime.strptime(os.environ["RSBV_START"], "%Y/%m/%d %H:%M:%S")
pid = int(os.environ["RSBV_PID"])
descendants = get_descendants(con, pid)
rstracer_processes = get_descendants(con, int(os.environ["RSBV_RSTRACER_PID"]))


st.set_page_config(
    page_title="Process",
    page_icon="⚙",
    layout="wide",
)
st.header("Process", divider=True)


# SLIDE BAR
st.sidebar.header("Parameters", divider=True)

show = st.sidebar.selectbox("Show only", ["launched processes", "new processes", "all processes"])

# Base filter arguments

filter_args = [
    [process.pid for process in descendants],
    show,
    analyse_start,
    show,
    show,
    [process.pid for process in rstracer_processes],
]

# Mem & Cpu Analysis

resource_per_command = con.execute(
    """
SELECT
    MAX(fact.pcpu) AS pcpu,
    MAX(fact.pmem) AS pmem,
    COALESCE(dim.command, dim.full_command) AS command,
    TO_TIMESTAMP(FLOOR(EXTRACT('epoch' FROM fact.created_at))) AT TIME ZONE 'UTC' AS time,
FROM
    gold_fact_process fact
LEFT JOIN
    gold_dim_process dim ON fact.pid = dim.pid
WHERE ((fact.pid IN ? AND ? = 'launched processes')
OR (dim.started_at >= ? AND ? = 'new processes')
OR (? = 'all processes'))
AND fact.pid NOT IN ?
GROUP BY time, COALESCE(dim.command, dim.full_command)
ORDER BY time
""",
    filter_args,
).df()


st.subheader("CPU Usage by Command", divider=True)
st.area_chart(
    resource_per_command, x="time", y="pcpu", color="command", stack="center", x_label="date", y_label="CPU usage"
)
st.subheader("Memory Usage by Command", divider=True)
st.area_chart(
    resource_per_command,
    x="time",
    y="pmem",
    color="command",
    stack="center",
    x_label="date",
    y_label="Memory usage (%)",
)


# Process count

st.subheader("Process Repartition", divider=True)

# Process by Commands

process_by_command_count = con.execute(
    """
WITH process AS
(
    SELECT DISTINCT
        fact.pid,
        COALESCE(dim.command, dim.full_command) AS command,
    FROM
        gold_fact_process fact
    LEFT JOIN
        gold_dim_process dim ON fact.pid = dim.pid
    WHERE ((fact.pid IN ? AND ? = 'launched processes')
    OR (dim.started_at >= ? AND ? = 'new processes')
    OR (? = 'all processes'))
    AND fact.pid NOT IN ?
)
SELECT
    command,
    COUNT(*) AS count
FROM process
GROUP BY command
ORDER BY count DESC
""",
    filter_args,
).df()

st.text("Process total launched by command")
st.bar_chart(
    process_by_command_count,
    x="command",
    y="count",
    x_label="command",
    y_label="count",
    color="command",
)

# Process list

process_list = con.execute(
    """
SELECT DISTINCT
    started_at AS 'started at',
    pid,
    ppid,
    name AS user,
    full_command AS command,
FROM gold_dim_process
LEFT JOIN gold_file_user ON gold_file_user.uid = gold_dim_process.uid
WHERE ((pid IN ? AND ? = 'launched processes')
OR (started_at >= ? AND ? = 'new processes')
OR (? = 'all processes'))
AND pid NOT IN ?
ORDER BY started_at ASC
LIMIT 300
""",
    filter_args,
).df()

st.subheader("Process History", divider=True)
st.dataframe(process_list, use_container_width=True, hide_index=True)

# Statistics

st.sidebar.header("Statistics", divider=True)

# Sudo process count

st.sidebar.write("Command PID: ", pid)

st.sidebar.write("Command sub-processes: ", len(descendants))

# Process count

process_total = con.execute(
    """
SELECT
    COUNT(DISTINCT ROW(fact.pid, dim.started_at)) AS count,
FROM
    gold_fact_process fact
LEFT JOIN
    gold_dim_process pro ON fact.pid = pro.pid
LEFT JOIN gold_dim_process dim ON fact.pid = dim.pid
WHERE ((fact.pid IN ? AND ? = 'launched processes')
OR (dim.started_at >= ? AND ? = 'new processes')
OR (? = 'all processes'))
AND fact.pid NOT IN ?
""",
    filter_args,
).fetchone()[0]

st.sidebar.write("Process total: ", process_total)

# Running time
end_timer = timer()
st.sidebar.write("Running time: ", round(end_timer - start_timer, 4), " seconds")
