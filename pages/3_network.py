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
    page_title="Network Activity",
    page_icon="🛜",
    layout="wide",
)
st.header("Network Activity", divider=True)

# SLIDE BAR

st.sidebar.header("Parameters", divider=True)

show = st.sidebar.selectbox("Show only", ["all packet", "from launched processes", "new packet"])

# Base filter arguments

filter_args = [
    [process.pid for process in descendants],
    show,
    analyse_start,
    show,
    show,
    [process.pid for process in rstracer_processes],
]

# Process by network

st.subheader("Packet size by command", divider=True)

packet_process = con.execute(
    """
SELECT
    TO_TIMESTAMP(FLOOR(EXTRACT('epoch' FROM packet.created_at))) AT TIME ZONE 'UTC' AS time,
    COALESCE(pro.command, pro.full_command, 'Unknown') AS command,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet packet
LEFT JOIN gold_fact_process_network net_pro ON net_pro.packet_id = packet._id
LEFT JOIN gold_dim_process pro ON net_pro.pid = pro.pid
WHERE  ((net_pro.pid IN ? AND ? = 'from launched processes')
        OR (packet.created_at >= ? AND ? = 'new packet')
        OR (? = 'all packet'))
    AND COALESCE(net_pro.pid, -1) NOT IN ?
GROUP BY time, COALESCE(pro.command, pro.full_command, 'Unknown')
ORDER BY time
""",
    filter_args,
).df()

st.area_chart(
    data=packet_process,
    x="time",
    y="size",
    color="command",
    stack="center",
    x_label="date",
    y_label="size (Mo)",
)

# Packet list

st.subheader("Packet I/0 history", divider=True)

packets = con.execute(
    """
SELECT DISTINCT
    packet.created_at AS 'created',
    COALESCE(pro.command, pro.full_command, 'Unknown') AS command,
    HOST(ip.source_address::INET) AS 'sender address',
    ip.source_port AS 'sender port',
    HOST(ip.destination_address::INET) AS 'receiver address',
    ip.destination_port AS 'receiver port',
    length AS 'size (bytes)',
    send AS 'local source'
FROM gold_fact_network_packet packet
INNER JOIN gold_fact_process_network net_pro ON net_pro.packet_id = packet._id
LEFT JOIN gold_dim_process pro ON net_pro.pid = pro.pid
LEFT JOIN gold_fact_network_ip ip ON packet._id = ip._id
WHERE  ((net_pro.pid IN ? AND ? = 'from launched processes')
        OR (packet.created_at >= ? AND ? = 'new packet')
        OR (? = 'all packet'))
    AND COALESCE(net_pro.pid, -1) NOT IN ?
ORDER BY packet.created_at
""",
    filter_args,
).df()

st.dataframe(packets, use_container_width=True, hide_index=True)

# Protocols by size

st.subheader("Protocols repartition by size", divider=True)
protocols_size_row = st.columns(4)

# Interfaces

interface_by_size = con.execute(
    """
SELECT
    interface,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet
WHERE created_at >= ?
GROUP BY interface
""",
    [analyse_start],
).df()
with protocols_size_row[0]:
    st.bar_chart(
        interface_by_size, x="interface", y="size", x_label="interface", y_label="size (Mo)", color="interface"
    )

# Network

network_by_size = con.execute(
    """
SELECT
    COALESCE (network, 'unknown') AS network,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet
WHERE created_at >= ?
GROUP BY network
    """,
    [analyse_start],
).df()
with protocols_size_row[1]:
    st.bar_chart(network_by_size, x="network", y="size", x_label="network", y_label="size (Mo)", color="network")

# Transport

transport_by_size = con.execute(
    """
SELECT
    COALESCE (transport, 'unknown') AS transport,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet
WHERE created_at >= ?
AND network IS NOT NULL
GROUP BY transport
    """,
    [analyse_start],
).df()
with protocols_size_row[2]:
    st.bar_chart(
        transport_by_size, x="transport", y="size", x_label="transport", y_label="size (Mo)", color="transport"
    )

# Transport

application_by_size = con.execute(
    """
SELECT
    COALESCE (application, 'unknown') AS application,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet
WHERE created_at >= ?
AND transport IS NOT NULL
GROUP BY application
""",
    [analyse_start],
).df()
with protocols_size_row[3]:
    st.bar_chart(
        application_by_size,
        x="application",
        y="size",
        x_label="application",
        y_label="size (Mo)",
        color="application",
    )

# Foreign IP

st.subheader("Foreign IP", divider=True)
foreign_ip_column = st.columns(2, gap="large")

foreign_ip_traffic = con.execute(
    """
WITH ip AS
(
    SELECT
        fact.created_at,
        COALESCE(fip1.address, fip2.address)::INET AS address,
        CASE
            WHEN fip1.address IS NOT NULL THEN 0
            WHEN fip2.address IS NOT NULL THEN 1
        END AS send,
        pack.length,
    FROM gold_fact_network_ip fact
    LEFT JOIN (SELECT  address FROM  gold_dim_network_foreign_ip) fip1
    ON fact.source_address = fip1.address
    LEFT JOIN (SELECT  address FROM  gold_dim_network_foreign_ip) fip2
    ON fact.destination_address = fip2.address
    LEFT JOIN gold_fact_network_packet pack ON fact._id = pack._id
    WHERE NOT (fip1.address IS NULL AND fip2.address IS NULL)
    AND NOT (fip1.address IS NOT NULL AND fip2.address IS NOT NULL)
    AND fact.created_at >= ?
)
SELECT
    HOST(address) AS address,
    COUNT(*) AS count,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size,
    AVG(send) AS send,
    TO_TIMESTAMP(AVG(EPOCH(created_at))) AS avg_date
FROM ip
GROUP BY HOST(address)
ORDER BY size DESC
""",
    [analyse_start],
).df()

with foreign_ip_column[0]:
    st.scatter_chart(foreign_ip_traffic, x="avg_date", y="count", color="send", size="size", x_label="date")

with foreign_ip_column[1]:
    st.dataframe(
        foreign_ip_traffic.drop(["avg_date", "send"], axis=1).rename(columns={"size": "size (Mo)"}), hide_index=True
    )

st.text(
    """Each dot represents a unique foreign IP address. Date shows the average timestamp for packets sent or received.
Count indicates the total number of packets exchanged with the IP. Dot size reflects the packet size in megabytes (MB).

Dot color blue reflects the local host received more packets from this IP than sent (send=0).
Dot color white reflects the local host sent more packets to this IP than received (send=1)."""
)

# Local IP

st.subheader("Local IP", divider=True)
local_ip_column = st.columns(2, gap="large")

local_ip_traffic = con.execute(
    """
WITH ip AS
(
    SELECT
        fact.created_at,
        COALESCE(fip1.address, fip2.address)::INET AS address,
        CASE
            WHEN fip1.address IS NULL THEN 0
            WHEN fip2.address IS NULL THEN 1
        END AS send,
        pack.length,
    FROM gold_fact_network_ip fact
    LEFT JOIN (SELECT  address FROM  gold_dim_network_local_ip) fip1
    ON fact.source_address = fip1.address
    LEFT JOIN (SELECT  address FROM  gold_dim_network_local_ip) fip2
    ON fact.destination_address = fip2.address
    LEFT JOIN gold_fact_network_packet pack ON fact._id = pack._id
    WHERE NOT (fip1.address IS NULL AND fip2.address IS NULL)
    AND NOT (fip1.address IS NOT NULL AND fip2.address IS NOT NULL)
    AND fact.created_at >= ?
)
SELECT
    HOST(address) AS address,
    COUNT(*) AS count,
    ROUND(SUM(length) / (1024 * 1024), 3) AS size,
    AVG(send) AS send,
    TO_TIMESTAMP(AVG(EPOCH(created_at))) AS avg_date
FROM ip
GROUP BY HOST(address)
ORDER BY size DESC
""",
    [analyse_start],
).df()

with local_ip_column[0]:
    st.scatter_chart(
        local_ip_traffic,
        x="avg_date",
        y="count",
        color="send",
        size="size",
    )

with local_ip_column[1]:
    st.dataframe(
        local_ip_traffic.drop(["avg_date", "send"], axis=1).rename(columns={"size": "size (Mo)"}), hide_index=True
    )

st.text(
    """Each dot represents a unique local IP address. Date shows the average timestamp for packets sent or received.
Count indicates the total number of packets exchanged with the IP. Dot size reflects the packet size in megabytes (MB).

Dot color blue reflects this local IP received more packets than sent (send=0).
Dot color white reflects this local IP sent more packets than received (send=1)."""
)

# Local Port

st.subheader("Local Port", divider=True)
local_port_column = st.columns(2, gap="large")

local_port_traffic = con.execute(
    """
WITH ip
AS (
    SELECT fact.created_at
        ,CASE
            WHEN fip1.address IS NULL
                THEN fact.destination_port
            WHEN fip2.address IS NULL
                THEN fact.source_port
            END AS port
        ,CASE
            WHEN fip1.address IS NULL
                THEN 0
            WHEN fip2.address IS NULL
                THEN 1
            END AS send
        ,pack.length
        ,
    FROM gold_fact_network_ip fact
    LEFT JOIN (
        SELECT address
        FROM gold_dim_network_local_ip
        ) fip1 ON fact.source_address = fip1.address
    LEFT JOIN (
        SELECT address
        FROM gold_dim_network_local_ip
        ) fip2 ON fact.destination_address = fip2.address
    LEFT JOIN gold_fact_network_packet pack ON fact._id = pack._id
    WHERE NOT (
            fip1.address IS NULL
            AND fip2.address IS NULL
            )
        AND NOT (
            fip1.address IS NOT NULL
            AND fip2.address IS NOT NULL
            )
        AND fact.created_at >= ?
    )
SELECT ip.port
    ,COALESCE(dim.command, 'Unknown') AS command
    ,COUNT(*) AS count
    ,ROUND(SUM(ip.length) / (1024 * 1024), 3) AS size
    ,AVG(ip.send) AS send
    ,TO_TIMESTAMP(AVG(EPOCH(ip.created_at))) AS avg_date
FROM ip
LEFT JOIN gold_dim_network_open_port dim ON ip.port = dim.port
    AND ip.created_at >= dim.started_at
    AND ip.created_at <= dim.inserted_at
GROUP BY ip.port
    ,COALESCE(dim.command, 'Unknown')
ORDER BY size DESC
""",
    [analyse_start],
).df()

with local_port_column[0]:
    st.scatter_chart(
        local_port_traffic,
        x="avg_date",
        y="count",
        color="send",
        size="size",
    )
with local_port_column[1]:
    st.dataframe(
        local_port_traffic.drop(["avg_date", "send"], axis=1).rename(columns={"size": "size (Mo)"}),
        hide_index=True,
    )

st.text(
    """Each dot represents a unique local IP address. Date shows the average timestamp for packets sent or received.
Count indicates the total number of packets exchanged with the IP. Dot size reflects the packet size in megabytes (MB).

Dot color blue reflects this local port received more packets than sent (send=0).
Dot color white reflects this local port sent more packets than received (send=1)."""
)

# Statistics

st.sidebar.header("Statistics", divider=True)

# Packet count

packet_count = con.execute(
    """
SELECT
    COUNT(*) AS count
FROM gold_fact_network_packet
WHERE created_at >= ?
""",
    [analyse_start],
).fetchone()[0]
st.sidebar.write("Total packet: ", packet_count)

# Packet size (Mo)

packet_size = con.execute(
    """
SELECT
    ROUND(SUM(length) / (1024 * 1024), 3) AS size
FROM gold_fact_network_packet
WHERE created_at >= ?
""",
    [analyse_start],
).fetchone()[0]
st.sidebar.write("Total size: ", packet_size, " Mo")

# Listening port

listening_port = con.execute(
    """
SELECT
    COUNT(DISTINCT source_port) AS count
FROM gold_dim_network_socket
WHERE inserted_at >= ?
AND source_port IS NOT NULL
""",
    [analyse_start],
).fetchone()[0]
st.sidebar.write("Listening port: ", listening_port)

# Running time

end_timer = timer()
st.sidebar.write("Running time: ", round(end_timer - start_timer, 4), " seconds")
