#!/usr/bin/env python3

import sys  # Importuje moduł sys, który zapewnia dostęp do zmiennych i funkcji systemowych
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, '../lib/python')) # Dodaje ścieżkę do listy ścieżek modułów Pythona

import codecs  # Importuje moduł codecs, który obsługuje kodowanie tekstu
import errno  # Importuje moduł errno, który zawiera numery błędów systemowych
import glob  # Importuje moduł glob, który obsługuje wyszukiwanie plików za pomocą wzorców
import io  # Importuje moduł io, który obsługuje operacje wejścia/wyjścia
import os  # Importuje moduł os, który zapewnia funkcje interfejsu operacyjnego
import os.path  # Importuje podmoduł os.path, który obsługuje operacje na ścieżkach plików
import subprocess  # Importuje moduł subprocess, który obsługuje uruchamianie nowych procesów

from debian_linux import config  # Importuje moduł config z pakietu debian_linux
from debian_linux.debian import *  # Importuje wszystkie elementy z modułu debian w pakiecie debian_linux
from debian_linux.gencontrol import (
    Gencontrol as Base,
    merge_packages,
)  # Importuje klasę Gencontrol jako Base i funkcję merge_packages z modułu gencontrol
from debian_linux.utils import (
    Templates,
    read_control,
)  # Importuje klasy Templates i funkcję read_control z modułu utils


class Gencontrol(Base):  # Definiuje klasę Gencontrol dziedziczącą po klasie Base
    config_schema = {  # Definiuje schemat konfiguracji jako słownik
        "abi": {  # Sekcja ABI w schemacie
            "ignore-changes": config.SchemaItemList(),  # Lista elementów konfiguracji ABI ignorowanych zmian
        },
        "build": {  # Sekcja build w schemacie
            "debug-info": config.SchemaItemBoolean(),  # Boolean do informacji debugowania
        },
        "description": {  # Sekcja description w schemacie
            "parts": config.SchemaItemList(),  # Lista elementów konfiguracji opisu
        },
        "image": {  # Sekcja image w schemacie
            "bootloaders": config.SchemaItemList(),  # Lista bootloaderów
            "configs": config.SchemaItemList(),  # Lista konfiguracji
            "initramfs-generators": config.SchemaItemList(),  # Lista generatorów initramfs
            "check-size": config.SchemaItemInteger(),  # Integer do sprawdzania rozmiaru
            "check-size-with-dtb": config.SchemaItemBoolean(),  # Boolean do sprawdzania rozmiaru z DTB
        },
        "relations": {},  # Sekcja relations w schemacie
    }

    def __init__(
        self, config_dirs=["debian/config"], template_dirs=["debian/templates"]
    ):  # Inicjalizuje instancję klasy
        super(
            Gencontrol, self
        ).__init__(  # Wywołuje konstruktor klasy bazowej z odpowiednimi argumentami
            config.ConfigCoreHierarchy(
                self.config_schema, config_dirs
            ),  # Inicjalizuje hierarchię konfiguracji z podanym schematem i katalogami konfiguracji
            Templates(
                template_dirs
            ),  # Inicjalizuje szablony z podanymi katalogami szablonów
            VersionLinux,
        )  # Przekazuje klasę VersionLinux jako argument
        self.process_changelog()  # Przetwarza dziennik zmian
        self.config_dirs = config_dirs  # Ustawia katalogi konfiguracji

    def _setup_makeflags(
        self, names, makeflags, data
    ):  # Definiuje metodę do ustawiania flag make
        for src, dst, optional in names:  # Iteruje przez pary źródło-cel i opcjonalność
            if (
                src in data or not optional
            ):  # Sprawdza, czy źródło jest w danych lub czy jest nieopcjonalne
                makeflags[dst] = data[src]  # Ustawia odpowiednią flagę make

    def _substitute_file(
        self, template, vars, target, append=False
    ):  # Definiuje metodę do podstawienia pliku
        with codecs.open(
            target, "a" if append else "w", "utf-8"
        ) as f:  # Otwiera plik w trybie dołączenia lub zapisu
            f.write(
                self.substitute(self.templates[template], vars)
            )  # Zapisuje podstawione wartości do pliku

    def do_main_setup(
        self, vars, makeflags, extra
    ):  # Definiuje metodę do głównej konfiguracji
        super(Gencontrol, self).do_main_setup(
            vars, makeflags, extra
        )  # Wywołuje metodę konfiguracji klasy bazowej
        makeflags.update(
            {  # Aktualizuje flagi make
                "VERSION": self.version.linux_version,  # Ustawia wersję
                "UPSTREAMVERSION": self.version.linux_upstream,  # Ustawia wersję upstream
                "ABINAME": self.version.linux_upstream
                + self.abiname_part,  # Ustawia nazwę ABI
                "SOURCEVERSION": self.version.complete,  # Ustawia pełną wersję
            }
        )

        """
        # Przygotowuje do wygenerowania debian/tests/control
        self.tests_control = None
        """

    def do_main_makefile(
        self, makefile, makeflags, extra
    ):  # Definiuje metodę do głównego pliku make
        fs_enabled = [
            featureset  # Tworzy listę włączonych zestawów funkcji
            for featureset in self.config["base",][
                "featuresets"
            ]  # Iteruje przez zestawy funkcji
            if self.config.merge("base", None, featureset).get("enabled", True)
        ]  # Sprawdza, czy zestaw funkcji jest włączony
        for featureset in fs_enabled:  # Iteruje przez włączone zestawy funkcji
            makeflags_featureset = makeflags.copy()  # Kopiuje flagi make
            makeflags_featureset[
                "FEATURESET"
            ] = featureset  # Ustawia flagę make dla zestawu funkcji
            cmds_source = [
                "$(MAKE) -f debian/rules.real source-featureset %s"  # Tworzy polecenia źródłowe
                % makeflags_featureset
            ]
            makefile.add(
                "source_%s_real" % featureset, cmds=cmds_source
            )  # Dodaje polecenie do pliku make
            makefile.add(
                "source_%s" % featureset,  # Dodaje polecenie do pliku make
                ["source_%s_real" % featureset],
            )
            makefile.add(
                "source", ["source_%s" % featureset]
            )  # Dodaje polecenie źródłowe do pliku make

        triplet_enabled = []  # Tworzy pustą listę włączonych tripletów
        for arch in iter(
            self.config[
                "base",
            ]["arches"]
        ):  # Iteruje przez architektury
            for featureset in self.config["base", arch].get(
                "featuresets", ()
            ):  # Iteruje przez zestawy funkcji
                if self.config.merge("base", None, featureset).get(
                    "enabled", True
                ):  # Sprawdza, czy zestaw funkcji jest włączony
                    for flavour in self.config["base", arch, featureset][
                        "flavours"
                    ]:  # Iteruje przez smaki
                        triplet_enabled.append(
                            "%s_%s_%s"
                            % (arch, featureset, flavour)  # Dodaje triplet do listy
                        )

        makeflags = makeflags.copy()  # Kopiuje flagi make
        makeflags["ALL_FEATURESETS"] = " ".join(
            fs_enabled
        )  # Ustawia wszystkie zestawy funkcji
        makeflags["ALL_TRIPLETS"] = " ".join(
            triplet_enabled
        )  # Ustawia wszystkie triplety
        super(Gencontrol, self).do_main_makefile(
            makefile, makeflags, extra
        )  # Wywołuje metodę pliku make klasy bazowej

        # linux-source-$UPSTREAMVERSION będzie zawierać wszystkie pliki kconfig
        makefile.add(
            "binary-indep", deps=["setup"]
        )  # Dodaje polecenie binarne niezależne do pliku make

    def do_main_packages(
        self, packages, vars, makeflags, extra
    ):  # Definiuje metodę do głównych pakietów
        packages.extend(
            self.process_packages(self.templates["control.main"], self.vars)
        )  # Rozszerza pakiety o przetworzone pakiety

    arch_makeflags = (  # Definiuje flagi make dla architektury
        ("kernel-arch", "KERNEL_ARCH", False),  # Flaga make dla architektury jądra
    )

    def do_arch_setup(
        self, vars, makeflags, arch, extra
    ):  # Definiuje metodę do konfiguracji architektury
        config_base = self.config.merge(
            "base", arch
        )  # Łączy konfigurację bazową dla architektury

        self._setup_makeflags(
            self.arch_makeflags, makeflags, config_base
        )  # Ustawia flagi make dla architektury

    def do_arch_packages(
        self, packages, makefile, arch, vars, makeflags, extra
    ):  # Definiuje metodę do pakietów architektury
        # Niektóre architektury użytkownika wymagają jądra z innej architektury (np. x32/amd64)
        foreign_kernel = not self.config["base", arch].get(
            "featuresets"
        )  # Sprawdza, czy architektura jest obca (brak zestawów funkcji)

        if (
            self.version.linux_modifier is None
        ):  # Jeśli nie ma modyfikatora wersji jądra
            try:
                abiname_part = (
                    ".%s" % self.config["abi", arch]["abiname"]
                )  # Próbuj ustawić część nazwy ABI
            except KeyError:
                abiname_part = (
                    self.abiname_part
                )  # Jeśli wystąpił błąd, użyj domyślnej części nazwy ABI
            makeflags["ABINAME"] = vars["abiname"] = (
                self.version.linux_upstream + abiname_part
            )  # Ustaw flagi make i zmienną ABI

        """
        if foreign_kernel:
            packages_headers_arch = []
            makeflags['FOREIGN_KERNEL'] = True
        else:
            headers_arch = self.templates["control.headers.arch"]
            packages_headers_arch = self.process_packages(headers_arch, vars)

        libc_dev = self.templates["control.libc-dev"]
        packages_headers_arch[0:0] = self.process_packages(libc_dev, {})

        packages_headers_arch[-1]['Depends'].extend(PackageRelation())
        extra['headers_arch_depends'] = packages_headers_arch[-1]['Depends']

        merge_packages(packages, packages_headers_arch, arch)

        cmds_binary_arch = ["$(MAKE) -f debian/rules.real binary-arch-arch %s" % makeflags]
        makefile.add('binary-arch_%s_real' % arch, cmds=cmds_binary_arch)

        # Skrót do wspomagania bootstrappingu architektury
        makefile.add('binary-libc-dev_%s' % arch,
                     ['source_none_real'],
                     ["$(MAKE) -f debian/rules.real install-libc-dev_%s %s" %
                      (arch, makeflags)])

        if os.getenv('DEBIAN_KERNEL_DISABLE_INSTALLER'):
            if self.changelog[0].distribution == 'UNRELEASED':
                import warnings
                warnings.warn('Disable installer modules on request (DEBIAN_KERNEL_DISABLE_INSTALLER set)')
            else:
                raise RuntimeError('Unable to disable installer modules in release build (DEBIAN_KERNEL_DISABLE_INSTALLER set)')
        else:
            # Dodaj udebs używając kernel-wedge
            installer_def_dir = 'debian/installer'
            installer_arch_dir = os.path.join(installer_def_dir, arch)
            if os.path.isdir(installer_arch_dir):
                kw_env = os.environ.copy()
                kw_env['KW_DEFCONFIG_DIR'] = installer_def_dir
                kw_env['KW_CONFIG_DIR'] = installer_arch_dir
                kw_proc = subprocess.Popen(
                    ['kernel-wedge', 'gen-control', vars['abiname']],
                    stdout=subprocess.PIPE,
                    env=kw_env)
                if not isinstance(kw_proc.stdout, io.IOBase):
                    udeb_packages = read_control(io.open(kw_proc.stdout.fileno(), encoding='utf-8', closefd=False))
                else:
                    udeb_packages = read_control(io.TextIOWrapper(kw_proc.stdout, 'utf-8'))
                kw_proc.wait()
                if kw_proc.returncode != 0:
                    raise RuntimeError('kernel-wedge exited with code %d' %
                                       kw_proc.returncode)

                merge_packages(packages, udeb_packages, arch)

                # Te pakiety muszą być budowane po pakietach na smak/per-featureset.
                # Również to nie będzie działać poprawnie z pustą listą pakietów.
                if udeb_packages:
                    makefile.add(
                        'binary-arch_%s' % arch,
                        cmds=["$(MAKE) -f debian/rules.real install-udeb_%s %s "
                              "PACKAGE_NAMES='%s'" %
                              (arch, makeflags,
                               ' '.join(p['Package'] for p in udeb_packages))])
        """

    def do_featureset_setup(
        self, vars, makeflags, arch, featureset, extra
    ):  # Definiuje metodę do konfiguracji zestawu funkcji
        config_base = self.config.merge(
            "base", arch, featureset
        )  # Łączy konfigurację bazową dla zestawu funkcji
        makeflags["LOCALVERSION_HEADERS"] = vars["localversion_headers"] = vars[
            "localversion"
        ]  # Ustawia flagi wersji lokalnej dla nagłówków

    def do_featureset_packages(
        self, packages, makefile, arch, featureset, vars, makeflags, extra
    ):  # Definiuje metodę do pakietów zestawu funkcji
        """
        headers_featureset = self.templates["control.headers.featureset"]
        package_headers = self.process_package(headers_featureset[0], vars)

        merge_packages(packages, (package_headers,), arch)

        cmds_binary_arch = ["$(MAKE) -f debian/rules.real binary-arch-featureset %s" % makeflags]
        makefile.add('binary-arch_%s_%s_real' % (arch, featureset), cmds=cmds_binary_arch)
        """

    flavour_makeflags_base = (  # Definiuje bazowe flagi make dla smaku
        ("compiler", "COMPILER", False),  # Flaga kompilatora
        ("kernel-arch", "KERNEL_ARCH", False),  # Flaga architektury jądra
        ("cflags", "CFLAGS_KERNEL", True),  # Flaga CFLAGS jądra
        (
            "override-host-type",
            "OVERRIDE_HOST_TYPE",
            True,
        ),  # Flaga nadpisania typu hosta
    )

    flavour_makeflags_build = (  # Definiuje flagi make dla budowania smaku
        ("image-file", "IMAGE_FILE", True),  # Flaga pliku obrazu
    )

    flavour_makeflags_image = (  # Definiuje flagi make dla obrazu smaku
        ("install-stem", "IMAGE_INSTALL_STEM", True),  # Flaga instalacji obrazu
    )

    flavour_makeflags_other = (  # Definiuje inne flagi make dla smaku
        ("localversion", "LOCALVERSION", False),  # Flaga wersji lokalnej
        (
            "localversion-image",
            "LOCALVERSION_IMAGE",
            True,
        ),  # Flaga wersji lokalnej obrazu
    )

    def do_flavour_setup(
        self, vars, makeflags, arch, featureset, flavour, extra
    ):  # Definiuje metodę do konfiguracji smaku
        config_base = self.config.merge(
            "base", arch, featureset, flavour
        )  # Łączy konfigurację bazową dla smaku
        config_build = self.config.merge(
            "build", arch, featureset, flavour
        )  # Łączy konfigurację budowania dla smaku
        config_description = self.config.merge(
            "description", arch, featureset, flavour
        )  # Łączy konfigurację opisu dla smaku
        config_image = self.config.merge(
            "image", arch, featureset, flavour
        )  # Łączy konfigurację obrazu dla smaku

        vars["class"] = config_description["hardware"]  # Ustawia klasę opisu sprzętu
        vars["longclass"] = (
            config_description.get("hardware-long") or vars["class"]
        )  # Ustawia długą klasę opisu sprzętu

        vars["localversion-image"] = vars[
            "localversion"
        ]  # Ustawia wersję lokalną obrazu
        override_localversion = config_image.get(
            "override-localversion", None
        )  # Pobiera nadpisaną wersję lokalną
        if override_localversion is not None:  # Jeśli nadpisana wersja lokalna istnieje
            vars["localversion-image"] = (
                vars["localversion_headers"] + "-" + override_localversion
            )  # Ustawia nadpisaną wersję lokalną obrazu
        vars["image-stem"] = config_image.get(
            "install-stem"
        )  # Pobiera instalacyjną nazwę obrazu

        self._setup_makeflags(
            self.flavour_makeflags_base, makeflags, config_base
        )  # Ustawia bazowe flagi make
        self._setup_makeflags(
            self.flavour_makeflags_build, makeflags, config_build
        )  # Ustawia flagi make dla budowania
        self._setup_makeflags(
            self.flavour_makeflags_image, makeflags, config_image
        )  # Ustawia flagi make dla obrazu
        self._setup_makeflags(
            self.flavour_makeflags_other, makeflags, vars
        )  # Ustawia inne flagi make

    def do_flavour_packages(
        self, packages, makefile, arch, featureset, flavour, vars, makeflags, extra
    ):  # Definiuje metodę do pakietów smaku
        headers = self.templates["control.headers"]  # Pobiera szablony nagłówków

        config_entry_base = self.config.merge(
            "base", arch, featureset, flavour
        )  # Łączy bazową konfigurację dla smaku
        config_entry_build = self.config.merge(
            "build", arch, featureset, flavour
        )  # Łączy konfigurację budowania dla smaku
        config_entry_description = self.config.merge(
            "description", arch, featureset, flavour
        )  # Łączy konfigurację opisu dla smaku
        config_entry_image = self.config.merge(
            "image", arch, featureset, flavour
        )  # Łączy konfigurację obrazu dla smaku
        config_entry_relations = self.config.merge(
            "relations", arch, featureset, flavour
        )  # Łączy konfigurację relacji dla smaku

        compiler = config_entry_base.get(
            "compiler", "gcc"
        )  # Pobiera kompilator, domyślnie gcc

        relations_compiler_headers = (
            PackageRelation(  # Tworzy relacje nagłówków kompilatora
                config_entry_relations.get("headers%" + compiler)
                or config_entry_relations.get(compiler)
            )
        )

        relations_compiler_build_dep = PackageRelation(
            config_entry_relations[compiler]
        )  # Tworzy relacje zależności budowania kompilatora
        for group in relations_compiler_build_dep:  # Iteruje przez grupy zależności
            for item in group:  # Iteruje przez elementy grupy
                item.arches = [arch]  # Ustawia architektury elementu
        packages["source"]["Build-Depends"].extend(
            relations_compiler_build_dep
        )  # Rozszerza zależności budowania źródła

        image_fields = {
            "Description": PackageDescription()
        }  # Tworzy opis pakietu obrazu
        for field in (
            "Depends",
            "Provides",
            "Suggests",
            "Recommends",
            "Conflicts",
            "Breaks",
        ):  # Iteruje przez pola zależności obrazu
            image_fields[field] = PackageRelation(
                config_entry_image.get(field.lower(), None), override_arches=(arch,)
            )  # Ustawia pole zależności obrazu

        generators = config_entry_image[
            "initramfs-generators"
        ]  # Pobiera generatory initramfs
        l = PackageRelationGroup()  # Tworzy grupę relacji pakietów
        for i in generators:  # Iteruje przez generatory
            i = config_entry_relations.get(i, i)  # Pobiera relację generatora
            l.append(i)  # Dodaje generator do grupy
            a = PackageRelationEntry(i)  # Tworzy wpis relacji pakietu
            if a.operator is not None:  # Jeśli operator istnieje
                a.operator = -a.operator  # Neguje operator
                image_fields["Breaks"].append(
                    PackageRelationGroup([a])
                )  # Dodaje wpis relacji do pola przerwań obrazu
        for item in l:  # Iteruje przez elementy grupy
            item.arches = [arch]  # Ustawia architektury elementu
        image_fields["Depends"].append(l)  # Dodaje grupę relacji do zależności obrazu

        bootloaders = config_entry_image.get("bootloaders")  # Pobiera bootloadery
        if bootloaders:  # Jeśli bootloadery istnieją
            l = PackageRelationGroup()  # Tworzy grupę relacji pakietów
            for i in bootloaders:  # Iteruje przez bootloadery
                i = config_entry_relations.get(i, i)  # Pobiera relację bootloadera
                l.append(i)  # Dodaje bootloader do grupy
                a = PackageRelationEntry(i)  # Tworzy wpis relacji pakietu
                if a.operator is not None:  # Jeśli operator istnieje
                    a.operator = -a.operator  # Neguje operator
                    image_fields["Breaks"].append(
                        PackageRelationGroup([a])
                    )  # Dodaje wpis relacji do pola przerwań obrazu
            for item in l:  # Iteruje przez elementy grupy
                item.arches = [arch]  # Ustawia architektury elementu
            image_fields["Suggests"].append(
                l
            )  # Dodaje grupę relacji do sugestii obrazu

        desc_parts = self.config.get_merge(
            "description", arch, featureset, flavour, "parts"
        )  # Pobiera i łączy części opisu
        if desc_parts:  # Jeśli części opisu istnieją
            # XXX: Workaround, musimy obsłużyć wiele wpisów o tej samej nazwie
            parts = list(set(desc_parts))  # Tworzy listę unikalnych części
            parts.sort()  # Sortuje części
            desc = image_fields["Description"]  # Pobiera opis obrazu
            for part in parts:  # Iteruje przez części
                desc.append(
                    config_entry_description["part-long-" + part]
                )  # Dodaje długi opis części
                desc.append_short(
                    config_entry_description.get("part-short-" + part, "")
                )  # Dodaje krótki opis części

        packages_dummy = []  # Tworzy pustą listę pakietów dummy
        packages_own = []  # Tworzy pustą listę własnych pakietów

        image = self.templates["control.image"]  # Pobiera szablon obrazu

        vars.setdefault("desc", None)  # Ustawia domyślną wartość dla zmiennej desc

        image_main = self.process_real_image(
            image[0], image_fields, vars
        )  # Przetwarza rzeczywisty obraz
        packages_own.append(
            image_main
        )  # Dodaje przetworzony obraz do własnych pakietów
        packages_own.extend(
            self.process_packages(image[1:], vars)
        )  # Rozszerza własne pakiety o przetworzone pakiety

        package_headers = self.process_package(
            headers[0], vars
        )  # Przetwarza nagłówki pakietu
        package_headers["Depends"].extend(
            relations_compiler_headers
        )  # Rozszerza zależności nagłówków pakietu
        packages_own.append(
            package_headers
        )  # Dodaje nagłówki pakietu do własnych pakietów
        """
        extra['headers_arch_depends'].append('%s (= ${binary:Version})' % packages_own[-1]['Package'])
        """

        build_debug = config_entry_build.get(
            "debug-info"
        )  # Pobiera informację debugowania budowania

        if os.getenv(
            "DEBIAN_KERNEL_DISABLE_DEBUG"
        ):  # Jeśli zmienna środowiskowa DEBIAN_KERNEL_DISABLE_DEBUG jest ustawiona
            if (
                self.changelog[0].distribution == "UNRELEASED"
            ):  # Jeśli dystrybucja jest UNRELEASED
                import warnings  # Importuje moduł warnings

                warnings.warn(
                    "Disable debug infos on request (DEBIAN_KERNEL_DISABLE_DEBUG set)"
                )  # Wyświetla ostrzeżenie o wyłączeniu informacji debugowania
                build_debug = False  # Ustawia build_debug na False
            else:
                raise RuntimeError(
                    "Unable to disable debug infos in release build (DEBIAN_KERNEL_DISABLE_DEBUG set)"
                )  # Podnosi wyjątek, gdy nie można wyłączyć informacji debugowania w wersji wydanej

        if build_debug:  # Jeśli build_debug jest True
            makeflags["DEBUG"] = True  # Ustawia flagę DEBUG na True
            packages_own.extend(
                self.process_packages(self.templates["control.image-dbg"], vars)
            )  # Rozszerza własne pakiety o pakiety debugowania

        merge_packages(
            packages, packages_own + packages_dummy, arch
        )  # Łączy pakiety własne i dummy z głównymi pakietami

        """
        tests_control = self.process_package(
            self.templates['tests-control.main'][0], vars)
        tests_control['Depends'].append(
            PackageRelationGroup(image_main['Package'],
                                 override_arches=(arch,)))
        if self.tests_control:
            self.tests_control['Depends'].extend(tests_control['Depends'])
        else:
            self.tests_control = tests_control
        """

        def get_config(*entry_name):  # Definiuje funkcję do pobierania konfiguracji
            entry_real = (
                "image",
            ) + entry_name  # Tworzy rzeczywiste wejście konfiguracji
            entry = self.config.get(entry_real, None)  # Pobiera wejście konfiguracji
            if entry is None:  # Jeśli wejście nie istnieje
                return None  # Zwraca None
            return entry.get("configs", None)  # Zwraca konfiguracje wejścia

        def check_config_default(
            fail, f
        ):  # Definiuje funkcję do sprawdzania domyślnej konfiguracji
            for d in self.config_dirs[
                ::-1
            ]:  # Iteruje przez katalogi konfiguracji w odwrotnej kolejności
                f1 = d + "/" + f  # Tworzy pełną ścieżkę pliku
                if os.path.exists(f1):  # Jeśli plik istnieje
                    return [f1]  # Zwraca listę z plikiem
            if fail:  # Jeśli ma zakończyć się niepowodzeniem
                raise RuntimeError("%s unavailable" % f)  # Podnosi wyjątek
            return []  # Zwraca pustą listę

        def check_config_files(
            files,
        ):  # Definiuje funkcję do sprawdzania plików konfiguracji
            ret = []  # Tworzy pustą listę wyników
            for f in files:  # Iteruje przez pliki
                for d in self.config_dirs[
                    ::-1
                ]:  # Iteruje przez katalogi konfiguracji w odwrotnej kolejności
                    f1 = d + "/" + f  # Tworzy pełną ścieżkę pliku
                    if os.path.exists(f1):  # Jeśli plik istnieje
                        ret.append(f1)  # Dodaje plik do wyników
                        break  # Przerywa wewnętrzną pętlę
                else:
                    raise RuntimeError(
                        "%s unavailable" % f
                    )  # Podnosi wyjątek, gdy plik jest niedostępny
            return ret  # Zwraca listę wyników

        def check_config(
            default, fail, *entry_name
        ):  # Definiuje funkcję do sprawdzania konfiguracji
            configs = get_config(*entry_name)  # Pobiera konfiguracje
            if configs is None:  # Jeśli konfiguracje nie istnieją
                return check_config_default(
                    fail, default
                )  # Sprawdza domyślną konfigurację
            return check_config_files(configs)  # Sprawdza pliki konfiguracji

        kconfig = check_config("config", True)  # Sprawdza konfigurację główną
        kconfig.extend(
            check_config(
                "kernelarch-%s/config" % config_entry_base["kernel-arch"], False
            )
        )  # Rozszerza konfigurację o konfigurację architektury jądra
        kconfig.extend(
            check_config("%s/config" % arch, True, arch)
        )  # Rozszerza konfigurację o konfigurację architektury
        kconfig.extend(
            check_config("%s/config.%s" % (arch, flavour), False, arch, None, flavour)
        )  # Rozszerza konfigurację o konfigurację smaku
        kconfig.extend(
            check_config("featureset-%s/config" % featureset, False, None, featureset)
        )  # Rozszerza konfigurację o konfigurację zestawu funkcji
        kconfig.extend(
            check_config("%s/%s/config" % (arch, featureset), False, arch, featureset)
        )  # Rozszerza konfigurację o konfigurację architektury i zestawu funkcji
        kconfig.extend(
            check_config(
                "%s/%s/config.%s" % (arch, featureset, flavour),
                False,
                arch,
                featureset,
                flavour,
            )
        )  # Rozszerza konfigurację o konfigurację architektury, zestawu funkcji i smaku
        makeflags["KCONFIG"] = " ".join(kconfig)  # Ustawia flagę KCONFIG
        if build_debug:  # Jeśli build_debug jest True
            makeflags["KCONFIG_OPTIONS"] = "-o DEBUG_INFO=y"  # Ustawia opcje KCONFIG

        cmds_binary_arch = [
            "$(MAKE) -f debian/rules.real binary-arch-flavour %s" % makeflags
        ]  # Tworzy polecenia binarne dla architektury smaku
        if packages_dummy:  # Jeśli pakiety dummy istnieją
            cmds_binary_arch.append(
                "$(MAKE) -f debian/rules.real install-dummy DH_OPTIONS='%s' %s"
                % (" ".join("-p%s" % i["Package"] for i in packages_dummy), makeflags)
            )  # Dodaje polecenie instalacji dummy do poleceń binarnych
        cmds_build = [
            "$(MAKE) -f debian/rules.real build-arch-flavour %s" % makeflags
        ]  # Tworzy polecenia budowania dla architektury smaku
        cmds_setup = [
            "$(MAKE) -f debian/rules.real setup-arch-flavour %s" % makeflags
        ]  # Tworzy polecenia konfiguracji dla architektury smaku
        makefile.add(
            "binary-arch_%s_%s_%s_real" % (arch, featureset, flavour),
            cmds=cmds_binary_arch,
        )  # Dodaje polecenie binarne do pliku make
        makefile.add(
            "build-arch_%s_%s_%s_real" % (arch, featureset, flavour), cmds=cmds_build
        )  # Dodaje polecenie budowania do pliku make
        makefile.add(
            "setup_%s_%s_%s_real" % (arch, featureset, flavour), cmds=cmds_setup
        )  # Dodaje polecenie konfiguracji do pliku make

        # Podstawia wersję jądra itp. do skryptów maintainer, tłumaczeń i overrides lintian
        self._substitute_file(
            "headers.postinst",
            vars,
            "debian/linux-headers-%s%s.postinst"
            % (vars["abiname"], vars["localversion"]),
        )  # Podstawia wersję jądra do skryptu postinst nagłówków
        for name in [
            "postinst",
            "postrm",
            "preinst",
            "prerm",
        ]:  # Iteruje przez nazwy skryptów maintainer
            self._substitute_file(
                "image.%s" % name,
                vars,
                "debian/linux-image-%s%s.%s"
                % (vars["abiname"], vars["localversion"], name),
            )  # Podstawia wersję jądra do skryptów maintainer obrazu
        if build_debug:  # Jeśli build_debug jest True
            self._substitute_file(
                "image-dbg.lintian-override",
                vars,
                "debian/linux-image-%s%s-dbgsym.lintian-overrides"
                % (vars["abiname"], vars["localversion"]),
            )  # Podstawia wersję jądra do overrides lintian dla debugowania

    def process_changelog(self):  # Definiuje metodę do przetwarzania dziennika zmian
        act_upstream = self.changelog[
            0
        ].version.upstream  # Pobiera bieżącą wersję upstream
        versions = []  # Tworzy pustą listę wersji
        for i in self.changelog:  # Iteruje przez dziennik zmian
            if i.version.upstream != act_upstream:  # Jeśli wersja upstream jest inna
                break  # Przerywa pętlę
            versions.append(i.version)  # Dodaje wersję do listy
        self.versions = versions  # Ustawia wersje
        version = self.version = self.changelog[0].version  # Ustawia bieżącą wersję
        if (
            self.version.linux_modifier is not None
        ):  # Jeśli modyfikator wersji jądra istnieje
            self.abiname_part = ""  # Ustawia pustą część nazwy ABI
        else:
            self.abiname_part = (
                ".%s"
                % self.config[
                    "abi",
                ]["abiname"]
            )  # Ustawia część nazwy ABI z konfiguracji
        self.vars = {  # Ustawia zmienne
            "upstreamversion": self.version.linux_upstream,  # Wersja upstream
            "version": self.version.linux_version,  # Wersja jądra
            "source_upstream": self.version.upstream,  # Źródłowa wersja upstream
            "source_package": self.changelog[0].source,  # Źródłowy pakiet
            "abiname": self.version.linux_upstream + self.abiname_part,  # Nazwa ABI
        }
        self.config["version",] = {
            "source": self.version.complete,  # Ustawia pełną wersję w konfiguracji
            "upstream": self.version.linux_upstream,  # Ustawia wersję upstream w konfiguracji
            "abiname_base": self.version.linux_version,  # Ustawia bazową nazwę ABI w konfiguracji
            "abiname": (
                self.version.linux_upstream
                + self.abiname_part  # Ustawia nazwę ABI w konfiguracji
            ),
        }

        distribution = self.changelog[
            0
        ].distribution  # Pobiera dystrybucję z dziennika zmian
        if distribution in ("unstable",):  # Jeśli dystrybucja jest niestabilna
            if (
                version.linux_revision_experimental
                or version.linux_revision_backports
                or version.linux_revision_other
            ):
                raise RuntimeError(
                    "Can't upload to %s with a version of %s" % (distribution, version)
                )  # Podnosi wyjątek, gdy nie można wysłać do dystrybucji
        if distribution in ("experimental",):  # Jeśli dystrybucja jest eksperymentalna
            if (
                not version.linux_revision_experimental
            ):  # Jeśli wersja eksperymentalna jądra nie istnieje
                raise RuntimeError(
                    "Can't upload to %s with a version of %s" % (distribution, version)
                )  # Podnosi wyjątek, gdy nie można wysłać do dystrybucji
        if distribution.endswith("-security") or distribution.endswith(
            "-lts"
        ):  # Jeśli dystrybucja kończy się na -security lub -lts
            if not version.linux_revision_security or version.linux_revision_backports:
                raise RuntimeError(
                    "Can't upload to %s with a version of %s" % (distribution, version)
                )  # Podnosi wyjątek, gdy nie można wysłać do dystrybucji
        if distribution.endswith(
            "-backports"
        ):  # Jeśli dystrybucja kończy się na -backports
            if (
                not version.linux_revision_backports
            ):  # Jeśli wersja backports jądra nie istnieje
                raise RuntimeError(
                    "Can't upload to %s with a version of %s" % (distribution, version)
                )  # Podnosi wyjątek, gdy nie można wysłać do dystrybucji

    def process_real_image(self, entry, fields, vars):
        entry = self.process_package(entry, vars)
        for key, value in fields.items():  # Iteruje przez pola i ich wartości
            if key in entry:  # Jeśli klucz jest w pakiecie
                real = entry[key]  # Pobiera rzeczywistą wartość klucza
                real.extend(value)  # Rozszerza rzeczywistą wartość o nową wartość
            elif value:  # Jeśli wartość nie jest pusta
                entry[key] = value  # Ustawia wartość klucza w pakiecie
        return entry  # Zwraca przetworzony pakiet

    def write(self, packages, makefile):  # Definiuje metodę do zapisu
        self.write_config()  # Zapisuje konfigurację
        super(Gencontrol, self).write(
            packages, makefile
        )  # Wywołuje metodę zapisu klasy bazowej
        """
        self.write_tests_control()
        """

    def write_config(self):  # Definiuje metodę do zapisu konfiguracji
        f = open(
            "debian/config.defines.dump", "wb"
        )  # Otwiera plik do zapisu w trybie binarnym
        self.config.dump(f)  # Zrzuca konfigurację do pliku
        f.close()  # Zamyka plik

    def write_tests_control(self):  # Definiuje metodę do zapisu kontroli testów
        self.write_rfc822(
            codecs.open(
                "debian/tests/control", "w", "utf-8"
            ),  # Otwiera plik do zapisu w trybie tekstowym
            [self.tests_control],
        )  # Zapisuje kontrolę testów do pliku


if __name__ == "__main__":  # Jeśli skrypt jest uruchamiany bezpośrednio
    Gencontrol()()  # Tworzy instancję klasy Gencontrol i wywołuje ją
