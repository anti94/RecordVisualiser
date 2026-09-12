"""Profil C şema katmanı — C++ struct tanımlarının TOML tarifi.

Kayıt dosyalarını C++ tarafı üretir (`D-29`). Bu paket o dosyaların
yerleşimini **tarif eden** TOML şemasını okur, doğrular ve çalışma
zamanında okuma yapıları üretir.

Sözleşme: `docs/format/toml-schema.md`.
"""

from __future__ import annotations

from sonar_analyzer.io.schema._toml import load_path, loads

__all__ = ["load_path", "loads"]
