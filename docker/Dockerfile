FROM python:3.10

RUN apt-get update && apt-get install -y \
    git \
    stress-ng \
    nano \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libpq-dev \
    sqlite3 \
    cmake \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest \
    pipenv \
    poetry \
    colorama \
    requests \
    tox \
    setuptools \
    wheel 

COPY shaker_py/shaker /shaker
COPY docker/run_in_container.sh /run_in_container.sh
RUN chmod +x /run_in_container.sh

WORKDIR /shaker
ENTRYPOINT ["/run_in_container.sh"]
