FROM docker.lcogt.net/miniconda3:4.0.5
MAINTAINER Las Cumbres Observatory <webmaster@lco.global>

RUN pip install -r requirements.txt

RUN mkdir /home/archive  && /usr/sbin/groupadd -g 10000 "domainusers" \
        && /usr/sbin/useradd -g 10000 -d /home/archive -M -N -u 10087 archive \
        && chown -R archive:domainusers /home/archive

WORKDIR /lco/lco-throughput

RUN pip install -r requirements.txt


COPY . /lco/lco-throughput

RUN python /lco/lco-throughput/setup.py install

USER archive

ENV HOME /home/archive

WORKDIR /home/archive