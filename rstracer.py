import subprocess

import psutil


class Rstracer:

    def __init__(self, path):
        self.path = path
        self.process = None
        self.log_file = open("rstracer.log", "w")

    def __del__(self):
        if self.state() == "Running":
            self.stop()

    def launch(self):
        self.process = subprocess.Popen(["sudo", self.path], stdout=self.log_file, stderr=self.log_file)

    def state(self):
        if self.process is None:
            return "Not running"
        return "Running" if self.process.poll() is None else "Exited"

    def stop(self):
        if self.process is not None:
            child_processes = [
                proc for proc in psutil.process_iter(attrs=["pid", "ppid"]) if proc.info["ppid"] == self.process.pid
            ]
            for child in child_processes:
                subprocess.run(["sudo", "kill", "-SIGINT", str(child.info["pid"])])
            subprocess.run(["sudo", "kill", "-SIGINT", str(self.process.pid)])
