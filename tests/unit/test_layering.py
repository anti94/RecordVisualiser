"""Katman ayrımı kontrolü — `F1-005`.

Plan Bölüm 7.1: çekirdek katmanlar (domain, io, repository, processing) GUI'yi
bilmez. Bu kural yalnız belgeyle korunamaz; burada testle korunur.

Test, çekirdek paketleri **temiz bir alt süreçte** içe aktarır ve `sys.modules`
içinde Qt modülü oluşup oluşmadığına bakar. Aynı süreçte çalışsaydı, başka bir
testin daha önce içe aktardığı PySide6 sonucu yanıltırdı.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

CORE_PACKAGES = [
    "sonar_analyzer.domain",
    "sonar_analyzer.io",
    "sonar_analyzer.repository",
    "sonar_analyzer.processing",
]

FORBIDDEN_PREFIXES = ("PySide6", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph", "matplotlib")


@pytest.mark.parametrize("package", CORE_PACKAGES)
def test_core_package_does_not_import_gui(package: str) -> None:
    script = textwrap.dedent(f"""
        import sys
        import importlib

        importlib.import_module({package!r})

        forbidden = {FORBIDDEN_PREFIXES!r}
        leaked = sorted(
            name
            for name in sys.modules
            if name.split(".")[0] in forbidden
        )
        print(";".join(leaked))
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"{package} ice aktarilamadi:\n{result.stderr}"
    leaked = [name for name in result.stdout.strip().split(";") if name]
    assert not leaked, (
        f"{package} cekirdek katmandir ama GUI modulu yukledi: {leaked}. "
        "Plan Bolum 7.1: GUI bagimliligi yalnizca ui/ katmaninda olabilir."
    )
