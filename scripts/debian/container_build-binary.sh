#!/bin/bash

set -euo pipefail  # Ustawia tryb pracy bash na: zakończ przy błędzie, nieużywane zmienne są błędami, pipeline zakończy się przy pierwszym błędzie

# shellcheck source=env.sh
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"  # Załaduj skrypt env.sh znajdujący się w tym samym katalogu

function prepare_env {  # Definiuje funkcję prepare_env
    echo "[INFO ] Preparing build directory: $dir_build"  # Wyświetl komunikat informacyjny o przygotowaniu katalogu build
    mkdir -p "$dir_build"  # Utwórz katalog build, jeśli nie istnieje
    if [[ -d "$dir_build/$package_name" ]]; then  # Sprawdź, czy istnieje katalog package_name w build
        echo "[INFO ] Removing $dir_build/$package_name"  # Wyświetl komunikat informacyjny o usuwaniu katalogu package_name
        rm -rf "$dir_build/$package_name"  # Usuń katalog package_name
    fi

    echo "[INFO ] Creating folder $package_name in $dir_build/"  # Wyświetl komunikat informacyjny o tworzeniu katalogu package_name
    mkdir -pv "$dir_build/$package_name"  # Utwórz katalog package_name z opcją verbose

    echo "[INFO ] Copying source packages to $dir_build/"  # Wyświetl komunikat informacyjny o kopiowaniu pakietów źródłowych
    cp -arv "$dir_artifacts/"*${version}.* "$dir_build/"  # Skopiuj pakiety źródłowe do katalogu build

    if [[ ! -L "$dir_build/$package_source" ]]; then  # Sprawdź, czy nie istnieje dowiązanie symboliczne package_source
        echo "[INFO ] Missing symlink: $dir_build/$package_source, creating"  # Wyświetl komunikat informacyjny o tworzeniu dowiązania symbolicznego
        ln -sf "$dir_base/$package_source" "$dir_build/$package_source"  # Utwórz dowiązanie symboliczne do package_source
    fi

    cd "$dir_build"  # Przejdź do katalogu build

    echo "[INFO ] Extracting source package to $dir_build/$package_name-$version_kernel"  # Wyświetl komunikat informacyjny o rozpakowywaniu pakietu źródłowego
    dpkg-source -x "${package_name}_${version}.dsc"  # Rozpakuj pakiet źródłowy
}

declare arch=${1:-}  # Zadeklaruj zmienną 'arch' z pierwszego argumentu skryptu, domyślnie pustą
declare distro=${2:-}  # Zadeklaruj zmienną 'distro' z drugiego argumentu skryptu, domyślnie pustą
declare release=${3:-}  # Zadeklaruj zmienną 'release' z trzeciego argumentu skryptu, domyślnie pustą
declare build=${4:-${version_build}}  # Zadeklaruj zmienną 'build' z czwartego argumentu skryptu, domyślnie 'version_build'
declare version="$(get_release_version $distro $release $build)"  # Zadeklaruj zmienną 'version' uzyskując wersję za pomocą funkcji get_release_version

declare dir_build="/build"  # Zadeklaruj zmienną 'dir_build' jako '/build'
declare dir_artifacts="$dir_artifacts/$distro/$release"  # Zadeklaruj zmienną 'dir_artifacts' jako podkatalog 'dir_artifacts' z dystrybucją i wersją

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

prepare_env  # Wywołaj funkcję prepare_env

# Musimy zaktualizować listy pakietów, aby móc poprawnie zainstalować zależności
apt-get update  # Zaktualizuj listy pakietów

cd "$dir_build/$package_name-$version_kernel"  # Przejdź do katalogu z rozpakowanym pakietem źródłowym
mk-build-deps -ir -t 'apt-get -y'  # Zainstaluj zależności build za pomocą mk-build-deps

echo "[INFO ] Building binary package for $release"  # Wyświetl komunikat informacyjny o budowaniu pakietu binarnego
$schedtool dpkg-buildpackage --build=binary  # Uruchom budowanie pakietu binarnego za pomocą dpkg-buildpackage

echo "[INFO ] Copying binary packages to bind mount: $dir_artifacts/"  # Wyświetl komunikat informacyjny o kopiowaniu pakietów binarnych
mkdir -p "$dir_artifacts"  # Utwórz katalog artifacts, jeśli nie istnieje

cp -arv "$dir_build/"*${version}_${arch}* "$dir_artifacts/"  # Skopiuj pakiety binarne do katalogu artifacts
