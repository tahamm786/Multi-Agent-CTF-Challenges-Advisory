FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dnsutils \
    file \
    binutils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests beautifulsoup4

WORKDIR /sandbox

# No CMD -- container is started fresh per execution, code is passed in at runtime