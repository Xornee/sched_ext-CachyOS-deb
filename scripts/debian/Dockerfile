# Deklaracja argumentów używanych podczas budowania obrazu
ARG ARCH
ARG DISTRO
ARG RELEASE

# Użycie podstawowego obrazu z odpowiedniej architektury, dystrybucji i wydania
FROM $ARCH/$DISTRO:$RELEASE

# Ustawienie zmiennej środowiskowej, aby uniknąć interaktywnej konfiguracji Debiana
ENV DEBIAN_FRONTEND=noninteractive

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update &&\
    apt-get install eatmydata -y &&\
    apt-get clean &&\
    rm -rfv /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libeatmydata.so
RUN apt-get update &&\
    apt-get dist-upgrade -y &&\
    apt-get install -y \
        build-essential \
        devscripts \
        equivs \
        wget \
        gnupg \
        schedtool &&\
    apt-get clean &&\
    rm -rfv /var/lib/apt/lists/*