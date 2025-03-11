# rstracer-behavior

[![CI](https://github.com/VictorMeyer77/rstracer-behavior/actions/workflows/ci.yml/badge.svg)](https://github.com/VictorMeyer77/rstracer-behavior/actions/workflows/ci.yml)

**Behavior Analysis Tool for UNIX Systems**

## Table of Contents

1. [About the Project](#about-the-project)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Configuration](#configuration)
7. [Limitations](#limitations)

---

## About the Project

**rstracer-behavior** is a powerful tool designed for analyzing system behaviors, such as process creation, file usage, and network activity, during command execution. Built on top of [rstracer](https://github.com/VictorMeyer77/rstracer), this tool simplifies behavior analysis with an intuitive interface and optional containerized deployment.

---

## Features

- **Comprehensive Analysis**:
  - Monitor processes created by commands.
  - Analyze open files and network activity in real-time.
- **User-Friendly Interface**:
  - Includes a simple GUI for straightforward operation.
- **Flexible Deployment**:
  - Supports containerized environments via Docker for sandboxed usage.

---

## Prerequisites

Ensure the following dependencies are installed before proceeding:

1. **Install rstracer**:
   ```shell
   cargo install --git https://github.com/VictorMeyer77/rstracer.git --tag 0.1.1
   ```

2. **System Dependencies**:
   ```shell
   apt-get update && apt-get install -y \
       libpcap-dev \
       git \
       build-essential \
       lsof \
       dnsutils \
       python3-pip \
       sudo
   ```

---

## Installation

1. **Setup Virtual Environment**:
   ```shell
   make virtualenv
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```shell
   make install
   ```

3. **Resolve Graphviz Path Issue (if applicable)**:
   If you encounter a path-related error during lineage downloading, ensure Graphviz is installed:
   ```shell
   apt-get install graphviz
   ```

---

## Usage

### Running Locally
Start the application using Streamlit:
```shell
streamlit run rsbv.py
```

> **Note**: Due to network analysis capabilities, administrative permissions are required. If prompted for a password when launching the command, restart the application with the appropriate permissions to ensure accurate analysis.

### Running with Docker
To use a containerized version:
1. **Build the Docker Image**:
   ```shell
   docker build -t rsbv-image .
   ```

2. **Run the Container**:
   ```shell
   docker run -p 8501:8501 rsbv-image
   ```

Access the GUI at `http://localhost:8501`.

---

## Configuration

The application applies a default configuration. To customize options, edit the `rstracer.toml` file provided with the project. Refer to the file for detailed configuration options.

---

## Limitations

1. **System Language**:
   - The `ps` command requires the system language to be set to **English** for correct date parsing.
   
2. **Platform**:
   - This tool is designed exclusively for UNIX-based systems and is not compatible with Windows.
