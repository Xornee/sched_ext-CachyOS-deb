#!/bin/bash

set -euo pipefail  # Ustawia tryb pracy bash na: zakończ przy błędzie, nieużywane zmienne są błędami, pipeline zakończy się przy pierwszym błędzie

# shellcheck source=env.sh
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"  # Załaduj skrypt env.sh znajdujący się w tym samym katalogu

declare distro=${1:-}  # Zadeklaruj zmienną 'distro' z pierwszego argumentu skryptu, domyślnie pustą
declare release=${2:-}  # Zadeklaruj zmienną 'release' z drugiego argumentu skryptu, domyślnie pustą
declare build=${3:-${version_build}}  # Zadeklaruj zmienną 'build' z trzeciego argumentu skryptu, domyślnie 'version_build'
declare dir_build="/build"  # Zadeklaruj zmienną 'dir_build' jako '/build'
declare dir_artifacts="$dir_artifacts/$distro/$release"  # Zadeklaruj zmienną 'dir_artifacts' jako podkatalog 'dir_artifacts' z dystrybucją i wersją

declare -i fail=0  # Zadeklaruj zmienną całkowitoliczbową 'fail' i ustaw ją na 0

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

prepare_env  # Przygotuj środowisko (funkcja zdefiniowana w env.sh)

# Musimy zaktualizować listy pakietów, aby móc poprawnie zainstalować zależności
apt-get update  # Zaktualizuj listy pakietów

version="$(get_release_version $distro $release $build)"  # Uzyskaj wersję release za pomocą funkcji 'get_release_version'

echo "[INFO ] Building source package for $release"  # Wyświetl komunikat informacyjny o budowaniu pakietu źródłowego
build_source_package "$release" "$version"  # Zbuduj pakiet źródłowy dla podanej wersji

echo "[INFO ] Copying sources to bind mount: $dir_artifacts/"  # Wyświetl komunikat informacyjny o kopiowaniu źródeł
mkdir -p "$dir_artifacts"  # Utwórz katalogi, jeśli nie istnieją
cp -arv "$dir_build/"*$version* "$dir_artifacts/"  # Skopiuj źródła do katalogu 'dir_artifacts'
