#!/bin/bash

# Ustawienie trybu pracy skryptu:
# -e : zakończ skrypt, jeśli jakiekolwiek polecenie zakończy się błędem
# -u : zakończ skrypt, jeśli wystąpi odwołanie do niezadeklarowanej zmiennej
# -o pipefail : zakończ skrypt, jeśli jakiekolwiek polecenie w potoku zakończy się błędem
set -euo pipefail

# Wczytanie zmiennych środowiskowych z pliku env.sh
# shellcheck source=env.sh : komentarz dla narzędzia shellcheck, wskazujący plik źródłowy
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"

# Deklaracja zmiennej distro i przypisanie jej wartości pierwszego argumentu skryptu lub pustej wartości, jeśli brak argumentu
declare distro=${1:-}
# Deklaracja zmiennej release i przypisanie jej wartości drugiego argumentu skryptu lub pustej wartości, jeśli brak argumentu
declare release=${2:-}
# Deklaracja zmiennej build i przypisanie jej wartości trzeciego argumentu skryptu lub wartości domyślnej version_build
declare build=${3:-${version_build}}

# Deklaracja zmiennej całkowitoliczbowej fail i ustawienie jej wartości na 0
declare -i fail=0

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

docker run --net='host' \
    --rm \
    --tmpfs /build:exec \
    --ulimit nofile=524288:524288 \
    -v $dir_base:/sched_ext-CachyOS-deb \
    -t "linux-sched_ext_cachyos_$source_arch/$source_distro/$source_release" \
    /sched_ext-CachyOS-deb/scripts/debian/container_build-source.sh \
        $distro \
        $release \
        $build 



# docker run --net='host' \
#     --tmpfs /build:exec \
#     --ulimit nofile=524288:524288 \
#     -v $dir_base:/sched_ext-CachyOS-deb \
#     -t "linux-sched_ext_cachyos_$source_arch/$source_distro/$source_release" \
#     tail -f /dev/null



