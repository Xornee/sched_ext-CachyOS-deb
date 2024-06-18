#!/bin/bash

# Ustawienie trybu pracy skryptu:
# -e : zakończ skrypt, jeśli jakiekolwiek polecenie zakończy się błędem
# -u : zakończ skrypt, jeśli wystąpi odwołanie do niezadeklarowanej zmiennej
# -o pipefail : zakończ skrypt, jeśli jakiekolwiek polecenie w potoku zakończy się błędem
echo "dupa"

set -euo pipefail

# Wczytanie zmiennych środowiskowych z pliku env.sh
# shellcheck source=env.sh : komentarz dla narzędzia shellcheck, wskazujący plik źródłowy
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"

# Deklaracja zmiennej arch i przypisanie jej wartości pierwszego argumentu skryptu lub pustej wartości, jeśli brak argumentu
declare arch=${1:-}
# Deklaracja zmiennej distro i przypisanie jej wartości drugiego argumentu skryptu lub pustej wartości, jeśli brak argumentu
declare distro=${2:-}
# Deklaracja zmiennej release i przypisanie jej wartości trzeciego argumentu skryptu lub pustej wartości, jeśli brak argumentu
declare release=${3:-}

# Deklaracja zmiennej całkowitoliczbowej fail i ustawienie jej wartości na 0
declare -i fail=0

# Sprawdzenie, czy zmienna arch jest pusta
if [[ -z "$arch" ]]; then
    # Wypisanie komunikatu o błędzie, jeśli architektura nie jest ustawiona
    echo "[ERROR] No architecture set!"
    # Ustawienie zmiennej fail na 1, aby zasygnalizować błąd
    fail=1
fi

# Sprawdzenie, czy zmienna distro jest pusta
if [[ -z "$distro" ]]; then
    # Wypisanie komunikatu o błędzie, jeśli dystrybucja nie jest ustawiona
    echo "[ERROR] No distribution set!"
    # Ustawienie zmiennej fail na 1, aby zasygnalizować błąd
    fail=1
fi

# Sprawdzenie, czy zmienna release jest pusta
if [[ -z "$release" ]]; then
    # Wypisanie komunikatu o błędzie, jeśli wydanie nie jest ustawione
    echo "[ERROR] No release set!"
    # Ustawienie zmiennej fail na 1, aby zasygnalizować błąd
    fail=1
fi

# Sprawdzenie, czy zmienna fail jest równa 1
if [[ $fail -eq 1 ]]; then
    # Wypisanie komunikatu o błędzie i zakończenie skryptu, jeśli wystąpił błąd
    echo "[ERROR] Encountered a fatal error, cannot continue!"
    exit 1
fi
#
#
# To generalnie jest zjebane i nie działa pozniej podpisywanie - docker build sie wypierdala na łeb
#
#

# Zbudowanie ciągu identyfikującego wydanie
declare release_string="linux-sched_ext_cachyos_$arch/$distro/$release"

# Sprawdzenie, czy obraz Docker o nazwie zawierającej release_string już istnieje
if [[ "$(docker image ls)" == *"$release_string"* ]]; then
    # Wypisanie informacji, że obraz Docker już istnieje i zostanie zaktualizowany
    echo "[INFO ] $release_string: Docker image already built, performing update."

    # Uruchomienie kontenera Docker z obrazem o nazwie release_string i wykonanie aktualizacji systemu
    declare container_id=$(
        docker run --net='host' -d $release_string bash -c \
        'apt-get update && \
         apt-get dist-upgrade && \
         apt-get clean && \
         rm -rf /var/lib/apt/lists'
    )

    # Wypisanie ID uruchomionego kontenera
    echo "[INFO ] $release_string: Trailing container - $container_id"
    while true; do
        # Sprawdzenie, czy kontener o podanym ID nadal działa
        if [[ -n "$(docker container ls -q -f id=$container_id)" ]]; then
            # Czekanie sekundę, jeśli kontener nadal działa
            sleep 1
        else
            # Przerwanie pętli, jeśli kontener przestał działać
            break
        fi
    done

    # Wypisanie informacji o zatwierdzaniu zaktualizowanego kontenera do repozytorium
    echo "[INFO ] $release_string: Committing updated container to repository"
    # Zatwierdzenie zaktualizowanego kontenera jako nowy obraz Docker
    docker commit -m "Update system packages" "$container_id" "$release_string" > /dev/null

    # Wypisanie informacji o usuwaniu kontenera
    echo "[INFO ] $release_string: Removing container - $container_id"
    # Usunięcie kontenera
    docker container rm "$container_id" > /dev/null
else
    # Wypisanie informacji o braku obrazu Docker i rozpoczęciu budowy z Dockerfile
    echo "[INFO ] $release_string: Docker image not found, building with Dockerfile."
    # Budowanie nowego obrazu Docker z użyciem Dockerfile i przekazanie odpowiednich argumentów build
    docker build --network="host" --no-cache \
        -f "$dir_scripts/Dockerfile" \
        -t "$release_string" \
        --pull=true \
        --build-arg ARCH="$arch" \
        --build-arg DISTRO="$distro" \
        --build-arg RELEASE="$release" \
        $dir_base/ || true  # Komentarz informujący, że skrypt budowania Dockerfile nie powinien zatrzymywać skryptów wydania
fi
