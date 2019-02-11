#
# Build ClamAV
#
FROM centos:7 AS build_clamav

ARG CLAMAV_VERSION=0.101.1

RUN yum update -y && \
    yum install -y gcc gcc-c++ openssl-devel wget make

RUN wget https://www.clamav.net/downloads/production/clamav-${CLAMAV_VERSION}.tar.gz && \
    tar xvzf clamav-${CLAMAV_VERSION}.tar.gz && \
    cd clamav-${CLAMAV_VERSION} && \
    ./configure && \
    make && make install

# Initial update of AV databases
RUN mkdir -p /var/lib/clamav && \
    wget -t 5 -T 99999 -O /var/lib/clamav/main.cvd http://database.clamav.net/main.cvd && \
    wget -t 5 -T 99999 -O /var/lib/clamav/daily.cvd http://database.clamav.net/daily.cvd && \
    wget -t 5 -T 99999 -O /var/lib/clamav/bytecode.cvd http://database.clamav.net/bytecode.cvd

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

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y openssl java-1.8.0-openjdk curl python36 && \
    yum clean all && \
    python36 -m ensurepip && \
    python36 -m pip install "celery==${CELERY_VERSION}" "boto3==${BOTO3_VERSION}"

COPY --from=build_clamav /usr/local/ /usr/local/
COPY --from=build_clamav /var/lib/clamav/ /var/lib/clamav/
COPY --from=build_clamav_rest /target/clamav-rest-*.jar /clamav-rest/

# Add clamav user
RUN groupadd -r clamav && \
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
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini.asc /tini.asc
RUN gpg --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 595E85A6B1B4779EA4DAAEC70B588DFF0527A9B7 && \
        gpg --verify /tini.asc && \
        chmod a+x /tini

ADD celery-worker/ /celery-worker/
ADD docker-entrypoint.sh /

USER 1000

VOLUME /var/lib/clamav

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ['help']
