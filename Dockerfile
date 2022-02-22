FROM python:3.10
MAINTAINER Las Cumbres Observatory <webmaster@lco.global>

WORKDIR /lco/throughput

RUN apt-get update -y \
        && apt-get install --no-install-recommends -y less vim \
        && apt-get clean -y \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt .
RUN pip --no-cache-dir install --upgrade pip \
        && pip --no-cache-dir install -r requirements.txt --upgrade

COPY . .
RUN python setup.py install
