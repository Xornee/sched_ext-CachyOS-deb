#!/bin/bash

# Ustal ścieżkę katalogu, w którym znajduje się ten skrypt
dir_script="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Nazwa pakietu
package_name='linux-sched_ext_cachyos'

# Ustal ścieżkę bazową, dwa poziomy wyżej niż katalog skryptu
dir_base="${dir_script%/*/*}" # liquorix-package

# Ustal ścieżkę katalogu pakietu
dir_package="$dir_base/$package_name" # liquorix-package/linux-liquorix

# Ustal ścieżkę katalogu budowania
dir_build="$dir_base/build" # liquorix-package/build

# Ustal ścieżkę do skryptów dla Debiana
dir_scripts="$dir_base/scripts/debian" #liquorix-package/scripts/debian

# Ustal ścieżkę do katalogu z artefaktami #liquorix-package/artifacts
dir_artifacts="$dir_base/artifacts"

# Wyciągnij wersję pakietu z pliku changelog w katalogu debian
version_package="$( head -n1 "$dir_package"/debian/changelog | grep -Po '\d+\.\d+-\d+' )"

# Wyciągnij wersję jądra z wersji pakietu
version_kernel="$(  echo $version_package                    | grep -Po '\d+\.\d+' )"

# Wyciągnij główną wersję z wersji jądra
version_major="$(   echo $version_kernel                     | sed -r 's/\..*//' )"

# Ustal wersję budowania
version_build="1"

# Ustal nazwę źródła pakietu
package_source="${package_name}_${version_kernel}.orig.tar.xz"

# Architektura, dystrybucja i wydanie do budowania pakietów źródłowych
source_arch='amd64'
source_distro='debian'
source_release='bookworm'

# Wydania Debiana i Ubuntu, z którymi można budować pakiety
releases_debian=('bookworm' 'trixie' 'sid')

# Mirrory dla Debiana i Ubuntu
mirror_debian='http://deb.debian.org/debian'

# Ustal użytkownika budującego oraz jego katalog domowy
build_user="$(whoami)"
build_base=$(grep -E "^${build_user}:" /etc/passwd | cut -f6 -d:)

# Lista zależności potrzebnych do budowania
build_deps=(
    'debhelper'
    'devscripts'
    'fakeroot'
    'gcc'
    'gzip'
    'pigz'
    'xz-utils'
    'schedtool'
)

# Polecenie schedtool do zarządzania priorytetami procesów
schedtool='schedtool -D -n19 -e'

# Funkcja do uzyskania prawidłowej wersji wydania dla Debiana/Ubuntu
function get_release_version {
    local distro="${1:-}"  # Przypisanie pierwszego argumentu funkcji do zmiennej lokalnej distro, domyślnie pustej
    local release="${2:-}"  # Przypisanie drugiego argumentu funkcji do zmiennej lokalnej release, domyślnie pustej
    local build="${3:-${version_build}}"  # Przypisanie trzeciego argumentu funkcji do zmiennej lokalnej build, domyślnie ustawionej na wartość zmiennej version_build

    declare version="${version_package}.${build}~${release}"  # Deklaracja zmiennej lokalnej version jako pustej

    echo "$version"  # Zwrócenie zbudowanej wersji
}

# Funkcja do przygotowania środowiska budowania
function prepare_env {
    echo "[INFO ] Preparing build directory: $dir_build"  # Informuje o przygotowywaniu katalogu budowania
    mkdir -p "$dir_build"  # Tworzy katalog budowania, jeśli nie istnieje
    if [[ -d "$dir_build/$package_name" ]]; then  # Sprawdza, czy katalog pakietu już istnieje
        echo "[INFO ] Removing $dir_build/$package_name"  # Informuje o usuwaniu istniejącego katalogu pakietu
        rm -rf "$dir_build/$package_name"  # Usuwa istniejący katalog pakietu
    fi

    echo "[INFO ] Creating folder $package_name in $dir_build/"  # Informuje o tworzeniu katalogu pakietu w katalogu budowania
    mkdir -pv "$dir_build/$package_name"  # Tworzy katalog pakietu w katalogu budowania

    echo "[INFO ] Copying $package_name/debian to $dir_build/$package_name/"  # Informuje o kopiowaniu katalogu debian do katalogu budowania
    cp -raf "$dir_package/debian" "$dir_build/$package_name/"  # Kopiuje katalog debian do katalogu budowania pakietu

    # Fakeroot ma 15% szansy na błąd semop w Dockerze
    local maintainerclean='fakeroot debian/rules maintainerclean'  # Definiuje polecenie do czyszczenia za pomocą fakeroot
    if [[ "$(id -u)" == 0 ]]; then  # Sprawdza, czy użytkownik ma uprawnienia roota
        maintainerclean='debian/rules maintainerclean'  # Jeśli tak, zmienia polecenie czyszczenia na zwykłe bez fakeroot
    fi
    cd "$dir_build/$package_name"  # Przechodzi do katalogu budowania pakietu

    echo "[INFO ] Running '$maintainerclean'"  # Informuje o uruchamianiu polecenia czyszczenia
    $maintainerclean  # Uruchamia polecenie czyszczenia

    if [[ ! -L "$dir_build/$package_source" ]]; then  # Sprawdza, czy nie istnieje dowiązanie symboliczne do źródła pakietu
        echo "[INFO ] Missing symlink: $dir_build/$package_source, creating"  # Informuje o tworzeniu brakującego dowiązania symbolicznego
        ln -sf "$dir_base/$package_source" "$dir_build/$package_source"  # Tworzy dowiązanie symboliczne do źródła pakietu
    fi

    echo "[INFO ] Unpacking kernel source into package folder."  # Informuje o rozpakowywaniu źródła jądra do katalogu pakietu
    tar -xpf "$dir_base/$package_source" --strip-components=1 -C "$dir_build/$package_name"  # Rozpakowuje źródło jądra do katalogu pakietu, usuwając pierwszy poziom katalogów
}

# Funkcja do budowania pakietu źródłowego
function build_source_package {
    local release_name="$1"  # Nazwa wydania
    local release_version="$2"  # Wersja wydania

    cd "$dir_build/$package_name"  # Przechodzi do katalogu budowania pakietu

    echo "[INFO ] Updating changelog to: $release_version"  # Informuje o aktualizacji changelog do nowej wersji
    sed -r -i "1s/[^;]+(;.*)/$package_name ($release_version) $release_name\1/" debian/changelog  # Aktualizuje pierwszy wiersz w changelog, zmieniając wersję i nazwę wydania

    echo "[INFO ] Cleaning package"  # Informuje o czyszczeniu pakietu

    local clean='fakeroot debian/rules clean'  # Definiuje polecenie do czyszczenia za pomocą fakeroot

    # Fakeroot ma 15% szansy na błąd semop w Dockerze
    if [[ "$(id -u)" == 0 ]]; then  # Sprawdza, czy użytkownik ma uprawnienia roota
        clean='debian/rules clean'  # Jeśli tak, zmienia polecenie czyszczenia na zwykłe bez fakeroot
    fi

    $clean || $clean  # Uruchamia polecenie czyszczenia, jeśli pierwsze podejście się nie powiedzie, próbuje ponownie

    mk-build-deps -ir -t 'apt-get -y'  # Tworzy pakiety zależności i instaluje je za pomocą apt-get

    EDITOR="cat" \
    DPKG_SOURCE_COMMIT_MESSAGE="Automated changes through CI" \
    DPKG_SOURCE_COMMIT_OPTIONS="--include-removal" \
        dpkg-source --commit . ci.patch  # Komituje zmiany do źródła pakietu z odpowiednim komunikatem i opcjami

    echo "[INFO ] Making source package"  # Informuje o tworzeniu pakietu źródłowego
    $schedtool dpkg-buildpackage --build=source  # Buduje pakiet źródłowy za pomocą dpkg-buildpackage, z priorytetem procesora ustawionym przez schedtool
}
