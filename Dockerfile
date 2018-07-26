FROM docker.lcogt.net/miniconda3:4.0.5
MAINTAINER Las Cumbres Observatory <webmaster@lco.global>


RUN mkdir /home/archive  && /usr/sbin/groupadd -g 10000 "domainusers" \
        && /usr/sbin/useradd -g 10000 -d /home/archive -M -N -u 10087 archive \
        && chown -R archive:domainusers /home/archive

COPY . /lco/lco-throughput

WORKDIR /lco/lco-throughput

RUN pip install --upgrade pip

RUN pip install -r requirements.txt --upgrade

COPY . /lco/lco-throughput

USER archive

ENV HOME /lco/lco-throughput

# TODO: launch a web server for config data
# TODO: launch cron like instance for regular updates of photdb database

