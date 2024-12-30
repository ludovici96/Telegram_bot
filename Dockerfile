# Build stage
FROM ubuntu:24.04 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        make git zlib1g-dev libssl-dev gperf cmake g++ ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    git clone --recursive https://github.com/tdlib/telegram-bot-api.git /build/telegram-bot-api && \
    cd /build/telegram-bot-api && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. && \
    cmake --build . --target install

# Final stage
FROM ubuntu:24.04

WORKDIR /app

COPY --from=builder /build/telegram-bot-api/bin/telegram-bot-api /usr/local/bin/
COPY requirements/requirements.txt ./
COPY run.py ./
COPY entrypoint.sh ./entrypoint.sh

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libssl3 zlib1g python3-minimal python3-pip python3-venv ffmpeg \
        libsm6 libxext6 libxrender-dev libglib2.0-0 wget curl aria2 gnupg \
        python3-dev build-essential && \
    \
    # Add MongoDB repo
    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
        | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
          https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" \
        | tee /etc/apt/sources.list.d/mongodb-org-8.0.list && \
    \
    apt-get update && \
    apt-get install -y --no-install-recommends mongodb-org && \
    \
    # Remove the MongoDB GPG key
    rm -f /usr/share/keyrings/mongodb-server-8.0.gpg && \
    \
    # Create folders and fix permissions
    mkdir -p /data/db /var/log/mongodb /app/gallery-dl /app/yt-dlp && \
    chown -R mongodb:mongodb /data/db /var/log/mongodb && \
    chmod -R 777 /app/gallery-dl /app/yt-dlp && \
    \
    # Create and activate a virtual environment, install Python deps
    python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    \
    # Make your entrypoint executable
    chmod +x ./entrypoint.sh && \
    \
    # Remove build tools, package managers, caches, and anything not needed at runtime
    apt-get purge -y --auto-remove wget curl gnupg python3-dev build-essential \
        python3-pip python3-venv aria2 openssh-server openssh-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /root/.cache /tmp/* /var/cache/apt/* \
           /usr/share/man/* /usr/share/doc/* /usr/share/info/* /usr/share/locale/*

COPY src/ ./src/

ENV DOCKER_ENV=1

ENTRYPOINT ["./entrypoint.sh"]
