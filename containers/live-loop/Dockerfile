FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/motif-tap-venv
ENV PATH="/opt/motif-tap-venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gcc \
        git \
        libmotif-dev \
        libx11-dev \
        libxt-dev \
        make \
        openbox \
        python3 \
        python3-pip \
        python3-venv \
        x11-utils \
        xdotool \
        xnee \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv "${VIRTUAL_ENV}" \
    && python -m pip install --upgrade pip

WORKDIR /workspace/motif-tap-harness

COPY . .

RUN python -m pip install -e '.[dev]' \
    && make -C c clean \
    && make -C c

CMD ["bash"]
