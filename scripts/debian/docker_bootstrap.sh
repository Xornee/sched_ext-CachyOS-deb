#!/bin/bash

# Ustawienie trybu pracy skryptu:
# -e : zakończ skrypt, jeśli jakiekolwiek polecenie zakończy się błędem
# -u : zakończ skrypt, jeśli wystąpi odwołanie do niezadeklarowanej zmiennej
# -o pipefail : zakończ skrypt, jeśli jakiekolwiek polecenie w potoku zakończy się błędem
set -euo pipefail

# Wczytanie zmiennych środowiskowych z pliku env.sh
# shellcheck source=env.sh : komentarz dla narzędzia shellcheck, wskazujący plik źródłowy
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"

# Uruchomienie skryptu common_bootstrap.sh znajdującego się w katalogu $dir_scripts
"$dir_scripts"/common_bootstrap.sh

# Przejście do katalogu $dir_scripts
cd "$dir_scripts"

# Sprawdzenie, czy polecenie docker jest zainstalowane
# Jeśli nie jest, wypisz komunikat o błędzie i zakończ skrypt
if ! command -v docker > /dev/null; then
    echo "[ERROR] Docker is not installed, cannot continue!"
    exit 1
fi

# Deklaracja zmiennej całkowitoliczbowej processes_default i ustawienie jej wartości na 2
declare -i processes_default=2
# Deklaracja zmiennej całkowitoliczbowej processes
# Jeśli pierwszy argument skryptu ($1) jest ustawiony, przypisz jego wartość do zmiennej processes, w przeciwnym razie użyj wartości domyślnej
declare -i processes=${1:-"$processes_default"}

# Sprawdzenie, czy wartość zmiennej processes jest równa wartości domyślnej
# Jeśli tak, wypisz informację o używaniu domyślnej liczby procesów
# W przeciwnym razie, wypisz informację o używaniu nadpisanej liczby procesów
if [[ $processes -eq $processes_default ]]; then
    echo "[INFO ] Using default process count, $processes"
else
    echo "[INFO ] Using override process count, $processes"
fi

# Deklaracja tablicy architectures i przypisanie jej wartości 'amd64'
declare -a architectures=('amd64')
# Deklaracja tablicy distros i przypisanie jej wartości 'debian' i 'ubuntu'
declare -a distros=('debian' 'ubuntu')
# Deklaracja pustej tablicy args
declare -a args=()

# Iteracja po wszystkich elementach tablicy architectures
for arch in "${architectures[@]}"; do
    # Iteracja po wszystkich elementach tablicy distros
    for distro in "${distros[@]}"; do
        # Deklaracja pustej tablicy releases
        declare -a releases=()
        # Sprawdzenie, czy zmienna distro jest równa 'debian'
        # Jeśli tak, przypisz wartości z tablicy releases_debian do tablicy releases
        if [[ "$distro" == 'debian' ]]; then
            releases=("${releases_debian[@]}")
        # Jeśli zmienna distro jest równa 'ubuntu', przypisz wartości z tablicy releases_ubuntu do tablicy releases
        elif [[ "$distro" == 'ubuntu' ]]; then
            releases=("${releases_ubuntu[@]}")
        fi

        # Iteracja po wszystkich elementach tablicy releases
        for release in "${releases[@]}"; do
            # Dodanie elementów arch, distro i release do tablicy args
            args+=("$arch" "$distro" "$release")
        done
    done
done

# Przekazanie elementów tablicy args do skryptu docker_bootstrap-image.sh za pomocą polecenia xargs
# -n3 : przekazanie trzech argumentów jednocześnie
# -P "$processes" : uruchomienie równoległe z maksymalnie $processes procesami
for item in "${args[@]}"; do
    echo "$item"
done | xargs -n3 -P "$processes" "$dir_scripts/docker_bootstrap-image.sh"
