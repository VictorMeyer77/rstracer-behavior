FROM rust:1.82.0-bullseye

RUN apt-get update && apt-get install -y \
    libpcap-dev \
    git \
    build-essential \
    lsof \
    dnsutils \
    python3-pip \
    sudo \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Install rstracer

RUN cargo install --git https://github.com/VictorMeyer77/rstracer.git --tag 0.1.0
RUN echo 'Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/cargo/bin/"' >> /etc/sudoers

# Install dashboard

ADD . /app
WORKDIR /app

RUN make install

EXPOSE 8501

# Launch task

ENTRYPOINT ["streamlit", "run", "rsbv.py", "--server.port=8501", "--server.address=0.0.0.0"]
