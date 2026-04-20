FROM python:3.14

WORKDIR /lco/throughput

RUN apt-get update -y \
        && apt-get install --no-install-recommends -y less vim \
        && apt-get clean -y \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


COPY . .
RUN pip --no-cache-dir install --upgrade pip \
        && pip --no-cache-dir install .
