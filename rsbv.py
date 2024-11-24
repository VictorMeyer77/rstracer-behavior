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
LOG_PATH = ".output/log"
RSTRACER_INIT_DURATION = 20


def get_descendants(pid):
    children = [proc.info["pid"] for proc in psutil.process_iter(attrs=["pid", "ppid"]) if proc.info["ppid"] == pid]
    for pid in children:
        children += get_descendants(pid)
    return children


def launch_behavior_analysis(command, user, lifetime, progress_bar):
    st.sidebar.warning(
        "Warning: This program requires sudo permissions. Please check your console to enter your password."
    )
    if not os.path.exists(".output/log/"):
        os.makedirs(".output/log/")
    log_file = open(".output/log/command.log", "w")
    os.environ["RSBV_START"] = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S")

    Rstracer().stop()
    os.environ["RSBV_RSTRACER_PID"] = str(Rstracer().launch())
    for percent_complete in range(RSTRACER_INIT_DURATION):
        sleep(1)
        progress_bar.progress(int(percent_complete / RSTRACER_INIT_DURATION * 100), text="Analysing the environment...")

    process = subprocess.Popen(f"sudo -u {user} {command}", stdout=log_file, stderr=log_file, shell=True)
    os.environ["RSBV_PID"] = str(process.pid)
    for percent_complete in range(lifetime):
        sleep(1)
        progress_bar.progress(int(percent_complete / lifetime * 100), text="Analysing your command...")

    stop_behavior_analysis(progress_bar)


def stop_behavior_analysis(progress_bar):
    progress_bar.progress(90, text="Stop rstracer...")
    pid = int(os.environ["RSBV_PID"])
    Rstracer().stop()
    for pid in [pid] + get_descendants(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
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

    button_column = st.columns(2)
    progress_bar = st.progress(0, text="")

    with button_column[0]:
        if st.button("Launch 🚀"):
            launch_behavior_analysis(command, user, lifetime, progress_bar)

    with button_column[1]:
        if st.button("Stop"):
            stop_behavior_analysis(progress_bar)


if __name__ == "__main__":
    run()
