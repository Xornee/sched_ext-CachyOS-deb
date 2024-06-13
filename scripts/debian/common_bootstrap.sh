#!/bin/bash

# Ustawienie trybu pracy skryptu:
# -e : zakończ skrypt, jeśli jakiekolwiek polecenie zakończy się błędem
# -u : zakończ skrypt, jeśli wystąpi odwołanie do niezadeklarowanej zmiennej
# -o pipefail : zakończ skrypt, jeśli jakiekolwiek polecenie w potoku zakończy się błędem
set -euo pipefail

# Wczytanie zmiennych środowiskowych z pliku env.sh
# shellcheck source=env.sh : komentarz dla narzędzia shellcheck, wskazujący plik źródłowy
source "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/env.sh"

# Sprawdzenie, czy plik źródłowy pakietu istnieje
if [[ ! -f "$dir_base/$package_source" ]]; then
    # Jeśli plik źródłowy nie istnieje, wypisz ostrzeżenie
    echo "[WARN ] Missing source file: $dir_base/$package_source, downloading now."
    
    # Pobierz plik źródłowy z internetu, używając wget
    wget -O "$dir_base/$package_source" "https://cdn.kernel.org/pub/linux/kernel/v${version_major}.x/linux-${version_kernel}.tar.xz"
fi
