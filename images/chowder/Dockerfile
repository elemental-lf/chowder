#
# Build ClamAV
#
FROM centos:7 AS build_clamav

ARG CLAMAV_VERSION=0.101.1

RUN yum update -q -y && \
    yum install -q -y gcc gcc-c++ openssl-devel pcre2-devel bzip2-devel libxml2-devel wget make

RUN wget -q -t 5 -T 99999 https://www.clamav.net/downloads/production/clamav-${CLAMAV_VERSION}.tar.gz && \
    tar xzf clamav-${CLAMAV_VERSION}.tar.gz && \
    cd clamav-${CLAMAV_VERSION} && \
    ./configure -q && \
    make -s && make -s install

# Initial update of AV databases
RUN mkdir -p /var/lib/clamav && \
    wget -q -t 5 -T 99999 -O /var/lib/clamav/main.cvd http://database.clamav.net/main.cvd && \
    wget -q -t 5 -T 99999 -O /var/lib/clamav/daily.cvd http://database.clamav.net/daily.cvd && \
    wget -q -t 5 -T 99999 -O /var/lib/clamav/bytecode.cvd http://database.clamav.net/bytecode.cvd

#
# Build ClamAV Java Client
#
FROM maven:latest as build_clamav_java

COPY vendor/github.com/solita/clamav-java .
RUN mvn install -B -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn -DskipTests

#
# Build ClamAV REST API
#
FROM maven:latest as build_clamav_rest

COPY vendor/github.com/solita/clamav-rest .
# Copy Maven context so that we get the clamav-client.jar from build_clamav_java
COPY --from=build_clamav_java /root/.m2/ /root/.m2/
RUN mvn install -B -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn -DskipTests

FROM centos:7 AS run

ARG CELERY_VERSION=4.2.1
ARG BOTO3_VERSION=1.9.91

RUN yum update -q -y && \
    yum install -q -y epel-release && \
    yum install -q -y openssl pcre2 bzip2 libxml2 java-1.8.0-openjdk curl python36 && \
    yum clean -y all && \
    python36 -m ensurepip && \
    python36 -m pip install "celery==${CELERY_VERSION}" "boto3==${BOTO3_VERSION}"

COPY --from=build_clamav /usr/local/ /usr/local/
COPY --from=build_clamav /var/lib/clamav/ /var/lib/clamav/
COPY --from=build_clamav_rest /target/clamav-rest-*.jar /clamav-rest/

# Add clamav user
RUN groupadd -r -g 1000 clamav && \
    useradd -r -g clamav -u 1000 clamav -d /var/lib/clamav && \
    mkdir -p /var/lib/clamav /usr/local/share/clamav /var/run/clamav && \
    chmod 750 /var/run/clamav && \
    chown -R clamav:clamav /var/lib/clamav /usr/local/share/clamav /var/run/clamav /usr/local/etc/

# Configure Clam AV
ADD --chown=clamav:clamav ./*.conf /usr/local/etc/
ADD --chown=clamav:clamav eicar.com /
ADD --chown=clamav:clamav ./healthcheck-*.sh /

# Tini
ARG TINI_VERSION=v0.18.0
ADD images/chowder/tini-pgp-key-0527A9B7.txt /tini-pgp-key-0527A9B7.txt
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini.asc /tini.asc
RUN gpg --import /tini-pgp-key-0527A9B7.txt && \
        gpg --verify /tini.asc && \
        chmod a+x /tini && \
        rm -f /tini-pgp-key-0527A9B7.txt /tini.asc

ADD celery-worker/ /celery-worker/lib
RUN mkdir /celery-worker/config && \
    mv /celery-worker/lib/chowder/celeryconfig.py /celery-worker/config && \
    ln -s ../../config/celeryconfig.py /celery-worker/lib/chowder/celeryconfig.py
ADD docker-entrypoint.sh /

USER 1000

VOLUME /var/lib/clamav

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ['help']
