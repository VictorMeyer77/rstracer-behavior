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
    page_title="Files",
    page_icon="📄",
    layout="wide",
)
st.header("Regular Files", divider=True)


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

# Open files Count

st.subheader("Activity", divider=True)
open_files_chart_row = st.columns(2)

files_count = con.execute(
    """
SELECT
  COUNT(DISTINCT dim.name) AS count,
  TO_TIMESTAMP(FLOOR(EXTRACT('epoch' FROM fact.created_at))) AT TIME ZONE 'UTC' AS time,
FROM
  gold_fact_file_reg fact
  LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
  LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
  LEFT JOIN gold_dim_file_reg dim ON fact.pid = dim.pid AND fact.fd = dim.fd AND fact.node = dim.node
WHERE ((fact.pid IN ? AND ? = 'launched processes')
    OR (pro.started_at >= ? AND ? = 'new processes')
    OR (? = 'all processes'))
    AND fact.pid NOT IN ?
GROUP BY
  time
ORDER BY
  time
""", filter_args
).df()

st.text("Open files total")
st.line_chart(data=files_count, x="time", y="count", x_label="date", y_label="count")

# Modification I/0

st.subheader("Modification size by command", divider=True)

modification_by_commands = con.execute(
    """
SELECT
  TO_TIMESTAMP(FLOOR(EXTRACT('epoch' FROM created_at))) AT TIME ZONE 'UTC' AS time,
  command,
  SUM(
    (size::BIGINT - previous_size::BIGINT)
  ) / (1024 * 1024) AS write_mo,
FROM
(
    SELECT
      pro.command,
      fact.created_at,
      size,
      LAG(size, 1, 0) OVER (
        PARTITION BY fact.pid,
            fact.fd,
            fact.node
        ORDER BY
            fact.created_at
       ) AS previous_size,
    ROW_NUMBER() OVER (
        PARTITION BY fact.pid,
           fact.fd,
           fact.node
       ORDER BY
            fact.created_at
      ) AS row_num
   FROM
      gold_fact_file_reg fact
      LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
      LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
   WHERE
     ((fact.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
    AND fact.pid NOT IN ?
  )
WHERE
  SIZE <> previous_size
  AND row_num > 1
GROUP BY
 time,
 command
ORDER BY
 time
  """, filter_args
).df()


st.area_chart(
    modification_by_commands,
    x="time",
    y="write_mo",
    color="command",
    stack="center",
    x_label="date",
    y_label="size (Mo)",
)

# Open files list

st.subheader("History", divider=True)

show_only_modified_files = st.checkbox("Show only modified files", value=True)

files_list = con.execute(
    """
SELECT
  pid,
  command,
  user,
  file,
  modification_size AS 'modification size (Mo)'
FROM
(
    SELECT
      fact.pid,
      pro.command,
      usr.name AS user,
      dim.name AS file,
      ROUND((MAX(size) - MIN(size)) / (1024 * 1024) , 3) AS modification_size
    FROM
      gold_fact_file_reg fact
      LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
      LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
      LEFT JOIN gold_dim_file_reg dim ON fact.pid = dim.pid AND fact.fd = dim.fd AND fact.node = dim.node
    WHERE
     ((fact.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
    AND fact.pid NOT IN ?
    GROUP BY
      fact.pid,
      pro.command,
      user,
      file
)
WHERE (modification_size > 0 OR NOT ?)
ORDER BY modification_size DESC
""", filter_args + [show_only_modified_files]
).df()

st.dataframe(files_list, use_container_width=True, hide_index=True)


# File by command

st.subheader("Command with most open files", divider=True)

file_by_command_count = con.execute(
    """
SELECT
  command,
  COUNT(DISTINCT file_name) AS count
FROM
(
    SELECT
      fact.pid,
      fact.fd,
      fact.node,
      pro.command,
      usr.name AS user_name,
      dim.name AS file_name,
      MIN(size) AS min_size,
      MAX(size) AS max_size
   FROM
      gold_fact_file_reg fact
      LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
      LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
      LEFT JOIN gold_dim_file_reg dim ON fact.pid = dim.pid AND fact.fd = dim.fd AND fact.node = dim.node
   WHERE
     ((fact.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
    AND fact.pid NOT IN ?
   GROUP BY
      fact.pid,
      fact.fd,
      fact.node,
      pro.command,
      user_name,
      file_name
  )
GROUP BY
 command
ORDER BY
 count DESC
""", filter_args
).df()

st.bar_chart(
    file_by_command_count,
    x="command",
    y="count",
    x_label="command",
    y_label="count",
    color="command",
)

# Statistics

st.sidebar.header("Statistics", divider=True)

# Open nodes

open_nodes = con.execute(
    """
SELECT
    COUNT(*) AS count
FROM
    gold_dim_file_reg file
    LEFT JOIN gold_dim_process pro ON file.pid = pro.pid
    WHERE ((file.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
    AND file.pid NOT IN ?
""", filter_args
).fetchone()[0]
st.sidebar.write("Opened nodes: ", open_nodes)

# Open files

open_files = con.execute(
    """
SELECT
    COUNT(DISTINCT file.name) AS count
FROM gold_dim_file_reg file
    LEFT JOIN gold_dim_process pro ON file.pid = pro.pid
    LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
    WHERE ((file.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
    AND file.pid NOT IN ?
""", filter_args,
).fetchone()[0]
st.sidebar.write("Opened files: ", open_files)

# Modified files

modified_files = con.execute(
    """
SELECT
  COUNT(*) AS count
FROM
(
    SELECT
      MIN(size) AS min_size,
      MAX(size) AS max_size
   FROM
      gold_fact_file_reg fact
     LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
     LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
     LEFT JOIN gold_dim_file_reg file ON fact.pid = file.pid
     AND fact.fd = file.fd
     AND fact.node = file.node
     WHERE ((file.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
     AND file.pid NOT IN ?
   GROUP BY
     file.name,
     )
WHERE
  max_size <> min_size
""", filter_args
).fetchone()[0]
st.sidebar.write("Modified files: ", modified_files)

# Modification size

modification_size = con.execute(
    """
SELECT
  ROUND(SUM(max_size - min_size) / (1024 * 1024), 3) AS write_mo
FROM
(
   SELECT
      MIN(size) AS min_size,
      MAX(size) AS max_size
   FROM
      gold_fact_file_reg fact
     LEFT JOIN gold_dim_process pro ON fact.pid = pro.pid
     LEFT JOIN gold_file_user usr ON pro.uid = usr.uid
     LEFT JOIN gold_dim_file_reg file ON fact.pid = file.pid
     AND fact.fd = file.fd
     AND fact.node = file.node
     WHERE ((file.pid IN ? AND ? = 'launched processes')
        OR (pro.started_at >= ? AND ? = 'new processes')
        OR (? = 'all processes'))
     AND file.pid NOT IN ?
   GROUP BY
      fact.pid,
     fact.fd,
     fact.node,
     file.name,
     )
WHERE
  max_size <> min_size
""", filter_args
).fetchone()[0]
st.sidebar.write("Modification size: ", modification_size, " Mo")

# Running time

end_timer = timer()
st.sidebar.write("Running time: ", round(end_timer - start_timer, 4), " seconds")
