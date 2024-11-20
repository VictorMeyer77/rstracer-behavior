import os
import signal
import subprocess
from datetime import datetime, timezone
from time import sleep

import psutil
import streamlit as st
from streamlit.logger import get_logger

from rstracer import Rstracer

LOGGER = get_logger(__name__)

RSTRACER_PATH = "rstracer"
RSTRACER_INIT_DURATION = 20


def get_descendants(pid):
    children = [proc.info["pid"] for proc in psutil.process_iter(attrs=["pid", "ppid"]) if proc.info["ppid"] == pid]
    for pid in children:
        children += get_descendants(pid)
    return children


def behavior(command, user, lifetime, st):

    log_file = open("command.log", "w")
    start = datetime.now(timezone.utc)
    rstracer = Rstracer(RSTRACER_PATH)
    progress_bar = st.progress(0, text="Analysing the environment...")
    rstracer.launch()
    for percent_complete in range(RSTRACER_INIT_DURATION):
        sleep(1)
        progress_bar.progress(int(percent_complete / RSTRACER_INIT_DURATION * 100), text="Analysing the environment...")

    process = subprocess.Popen(["sudo", "-u", user, command], stdout=log_file, stderr=log_file)
    for percent_complete in range(lifetime):
        sleep(1)
        progress_bar.progress(int(percent_complete / lifetime * 100), text="Analysing your command...")

    progress_bar.progress(90, text="Kill all processes")
    for pid in [process.pid] + get_descendants(process.pid):
        os.kill(pid, signal.SIGTERM)

    rstracer.stop()
    os.environ["RSBV_PID"] = str(process.pid)
    os.environ["RSBV_START"] = start.strftime("%Y/%m/%d %H:%M:%S")
    progress_bar.progress(100, text="Ready !")


def run():
    st.set_page_config(
        page_title="Behavior Analysis",
        page_icon="🔎",
    )

    st.write("# Behavior Analysis 🔎")

    command = st.text_input("Execute command")
    user = st.text_input("With user")
    lifetime = st.number_input("During", step=1)

    if st.button("Launch 🚀"):
        behavior(command, user, lifetime, st)


if __name__ == "__main__":
    run()
