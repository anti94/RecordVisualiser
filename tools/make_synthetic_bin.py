"""1 GB, 10 GB veya seçilen boyutta Profil B dosyasını parça parça üretir."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from tools.make_acoustic_fixture import iter_acoustic_fixture  # noqa: E402

from sonar_analyzer.io.profile_b_format import (  # noqa: E402
    ACOUSTIC_CHANNELS,
    ACOUSTIC_PAYLOAD_BYTES,
    BLOCK_HEADER_SIZE,
    CHANNEL_ENTRY,
    FILE_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_PERIOD_NS,
    RECORD_TRAILER_SIZE,
    SAMPLES_PER_BLOCK,
)

HEADER_BYTES = FILE_HEADER.size + len(ACOUSTIC_CHANNELS) * CHANNEL_ENTRY.size
RECORD_BYTES = (
    RECORD_HEADER_SIZE
    + len(ACOUSTIC_CHANNELS) * (BLOCK_HEADER_SIZE + ACOUSTIC_PAYLOAD_BYTES)
    + RECORD_TRAILER_SIZE
)
DEFAULT_SEED = 20260910


def specification(min_bytes: int, seed: int = DEFAULT_SEED) -> dict[str, int | str]:
    if min_bytes <= HEADER_BYTES or seed < 0:
        raise ValueError("Boyut header'dan büyük, seed negatif olmayan tam sayı olmalı")
    records = (min_bytes - HEADER_BYTES + RECORD_BYTES - 1) // RECORD_BYTES
    return {
        "profile": "B",
        "generator_version": 1,
        "seed": seed,
        "requested_min_bytes": min_bytes,
        "file_bytes": HEADER_BYTES + records * RECORD_BYTES,
        "header_bytes": HEADER_BYTES,
        "record_bytes": RECORD_BYTES,
        "record_count": records,
        "samples_per_channel": records * SAMPLES_PER_BLOCK,
        "duration_ns": records * RECORD_PERIOD_NS,
    }


def write_fixture(output: Path, min_bytes: int, seed: int = DEFAULT_SEED) -> dict[str, object]:
    spec = specification(min_bytes, seed)
    records = int(spec["record_count"])
    partial = output.with_name(output.name + ".partial")
    manifest = output.with_name(output.name + ".json")
    if output.exists() or manifest.exists():
        raise FileExistsError(f"Çıktı veya manifest zaten var: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    started = perf_counter()
    # Var olan partial da ezilmez. Kesintide yarım çıktı final adını alamaz.
    with partial.open("xb") as stream:
        for block in iter_acoustic_fixture(records, seed):
            stream.write(block)
            digest.update(block)
        stream.flush()
        os.fsync(stream.fileno())
    partial.rename(output)
    result: dict[str, object] = {
        **spec,
        "sha256": digest.hexdigest(),
        "generation_seconds": perf_counter() - started,
    }
    with manifest.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bytes", type=int, required=True, dest="min_bytes")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = (
        specification(args.min_bytes, args.seed)
        if args.dry_run
        else write_fixture(args.out, args.min_bytes, args.seed)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
