#!/bin/bash

set -euo pipefail  # Ustawia tryb pracy bash na: zakończ przy błędzie, nieużywane zmienne są błędami, pipeline zakończy się przy pierwszym błędzie

# shellcheck source=env.sh
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"  # Załaduj skrypt env.sh znajdujący się w tym samym katalogu

declare arch=${1:-}  # Zadeklaruj zmienną 'arch' z pierwszego argumentu skryptu, domyślnie pustą
declare distro=${2:-}  # Zadeklaruj zmienną 'distro' z drugiego argumentu skryptu, domyślnie pustą
declare release=${3:-}  # Zadeklaruj zmienną 'release' z trzeciego argumentu skryptu, domyślnie pustą
declare build=${4:-${version_build}}  # Zadeklaruj zmienną 'build' z czwartego argumentu skryptu, domyślnie 'version_build'

declare -i fail=0  # Zadeklaruj zmienną całkowitoliczbową 'fail' i ustaw ją na 0

if [[ -z "$arch" ]]; then  # Sprawdź, czy 'arch' jest puste
    echo "[ERROR] No architecture set!"  # Wyświetl komunikat o błędzie, jeśli 'arch' jest puste
    fail=1  # Ustaw 'fail' na 1
fi

if [[ -z "$distro" ]]; then  # Sprawdź, czy 'distro' jest puste
    echo "[ERROR] No distribution set!"  # Wyświetl komunikat o błędzie, jeśli 'distro' jest puste
    fail=1  # Ustaw 'fail' na 1
fi

if [[ -z "$release" ]]; then  # Sprawdź, czy 'release' jest puste
    echo "[ERROR] No release set!"  # Wyświetl komunikat o błędzie, jeśli 'release' jest puste
    fail=1  # Ustaw 'fail' na 1
fi

if [[ $fail -eq 1 ]]; then  # Sprawdź, czy 'fail' jest równe 1
    echo "[ERROR] Encountered a fatal error, cannot continue!"  # Wyświetl komunikat o błędzie krytycznym
    exit 1  # Zakończ skrypt z kodem błędu 1
fi

docker run --net='host' \
    --rm \
    --ulimit nofile=524288:524288 \
    -v $dir_base:/sched_ext-CachyOS-deb \
    -t "linux-sched_ext_cachyos_$arch/$distro/$release" \
    /sched_ext-CachyOS-deb/scripts/debian/container_build-binary.sh \
        $arch \
        $distro \
        $release \
        $build

