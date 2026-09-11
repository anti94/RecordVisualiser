"""Son geçerli workspace kurtarması — `F6-021`.

Kabul: **Kesinti sonrası sağlam oturum önerilir; bozuk dosya etkin
oturumu ezmez.**

İki yarı ayrı ayrı sınanır ve ikincisi asıl olandır. Bir kurtarma
mekanizmasının en kötü kusuru, kurtarmaya çalışırken elde olanı
bozmasıdır: bozuk bir kontrol noktasını yükleyip etkin oturumun üzerine
yazmak, kullanıcıyı kesintiden daha kötü bir yere bırakır.

Bu yüzden aday **önerilmeden önce okunur**; okunamıyorsa atlanır, hiçbiri
okunamıyorsa öneri yapılmaz.
"""

from __future__ import annotations

from pathlib import Path

from sonar_analyzer.workspace.model import PanelState, WorkspaceModel
from sonar_analyzer.workspace.recovery import (
    MAX_CHECKPOINTS,
    checkpoint_dir,
    discard_checkpoints,
    find_recoverable,
    list_checkpoints,
    write_checkpoint,
)


def _model(channel: str = "ch0") -> WorkspaceModel:
    return WorkspaceModel(
        source_paths=["C:/data/a.bin"],
        panels=[PanelState(channel_ids=[channel], x_range=(0.0, 5.0))],
        sync_groups=[[0]],
        active_view_tab="Time Series",
        dock_state="Zm9v",
    )


def _corrupt(path: Path) -> None:
    path.write_text("{ bu gecerli bir workspace degil", encoding="utf-8")


# --------------------------------------------------------------------------- #
# SAGLAM OTURUM ONERILIR
# --------------------------------------------------------------------------- #


def test_nothing_is_offered_when_there_is_no_checkpoint(tmp_path: Path) -> None:
    assert find_recoverable(tmp_path) is None


def test_a_written_checkpoint_can_be_recovered(tmp_path: Path) -> None:
    write_checkpoint(_model("ch3"), tmp_path)
    candidate = find_recoverable(tmp_path)

    assert candidate is not None
    assert candidate.model == _model("ch3")


def test_the_newest_checkpoint_is_offered(tmp_path: Path) -> None:
    write_checkpoint(_model("eski"), tmp_path)
    write_checkpoint(_model("yeni"), tmp_path)

    candidate = find_recoverable(tmp_path)
    assert candidate is not None
    assert candidate.model == _model("yeni")


def test_the_candidate_reports_when_it_was_saved(tmp_path: Path) -> None:
    """Kullanıcı "ne kadar eski" sorusuna cevap görmeli."""
    write_checkpoint(_model(), tmp_path)
    candidate = find_recoverable(tmp_path)

    assert candidate is not None
    assert candidate.age_seconds >= 0.0


# --------------------------------------------------------------------------- #
# BOZUK DOSYA ETKIN OTURUMU EZMEZ
# --------------------------------------------------------------------------- #


def test_a_corrupt_checkpoint_is_not_offered(tmp_path: Path) -> None:
    """Asıl kabul: bozuk dosya öneri olarak sunulmamalı."""
    write_checkpoint(_model(), tmp_path)
    for path in list_checkpoints(tmp_path):
        _corrupt(path)

    assert find_recoverable(tmp_path) is None


def test_a_corrupt_newest_falls_back_to_the_previous_good_one(tmp_path: Path) -> None:
    """En yeni bozuksa bir önceki sağlam olan önerilir."""
    write_checkpoint(_model("saglam"), tmp_path)
    write_checkpoint(_model("bozulacak"), tmp_path)

    newest = list_checkpoints(tmp_path)[0]
    _corrupt(newest)

    candidate = find_recoverable(tmp_path)
    assert candidate is not None
    assert candidate.model == _model("saglam")


def test_a_corrupt_checkpoint_is_not_deleted(tmp_path: Path) -> None:
    """Bozuk dosya tanılama için gerekebilir; önerilmez ama silinmez."""
    write_checkpoint(_model(), tmp_path)
    newest = list_checkpoints(tmp_path)[0]
    _corrupt(newest)

    find_recoverable(tmp_path)
    assert newest.is_file()


def test_finding_a_candidate_does_not_touch_any_checkpoint(tmp_path: Path) -> None:
    """Öneri bir okumadır; hiçbir şeyi yazmaz ya da taşımaz."""
    write_checkpoint(_model(), tmp_path)
    before = {path.name: path.read_bytes() for path in list_checkpoints(tmp_path)}

    find_recoverable(tmp_path)

    after = {path.name: path.read_bytes() for path in list_checkpoints(tmp_path)}
    assert after == before


def test_an_empty_file_is_treated_as_corrupt(tmp_path: Path) -> None:
    write_checkpoint(_model(), tmp_path)
    list_checkpoints(tmp_path)[0].write_text("", encoding="utf-8")

    assert find_recoverable(tmp_path) is None


# --------------------------------------------------------------------------- #
# KONTROL NOKTALARI SINIRLI
# --------------------------------------------------------------------------- #


def test_old_checkpoints_are_pruned(tmp_path: Path) -> None:
    """Oturum dizini sınırsız büyümemeli."""
    for index in range(MAX_CHECKPOINTS + 4):
        write_checkpoint(_model(f"ch{index}"), tmp_path)

    assert len(list_checkpoints(tmp_path)) == MAX_CHECKPOINTS


def test_pruning_keeps_the_newest(tmp_path: Path) -> None:
    for index in range(MAX_CHECKPOINTS + 2):
        write_checkpoint(_model(f"ch{index}"), tmp_path)

    candidate = find_recoverable(tmp_path)
    assert candidate is not None
    assert candidate.model == _model(f"ch{MAX_CHECKPOINTS + 1}")


def test_checkpoints_live_in_their_own_directory(tmp_path: Path) -> None:
    write_checkpoint(_model(), tmp_path)
    assert checkpoint_dir(tmp_path).is_dir()


# --------------------------------------------------------------------------- #
# KARAR VERILDIKTEN SONRA
# --------------------------------------------------------------------------- #


def test_discarding_removes_every_checkpoint(tmp_path: Path) -> None:
    """Temizlenmezse aynı öneri her açılışta tekrar gelir."""
    for index in range(3):
        write_checkpoint(_model(f"ch{index}"), tmp_path)

    removed = discard_checkpoints(tmp_path)

    assert removed == 3
    assert list_checkpoints(tmp_path) == []
    assert find_recoverable(tmp_path) is None


def test_discarding_an_empty_directory_is_harmless(tmp_path: Path) -> None:
    assert discard_checkpoints(tmp_path) == 0


def test_a_checkpoint_write_is_atomic(tmp_path: Path) -> None:
    """Yarıda kesilen yazım yarım dosya bırakmaz (`save_workspace` yolu)."""
    write_checkpoint(_model(), tmp_path)
    leftovers = list(checkpoint_dir(tmp_path).glob("*.part"))

    assert leftovers == []
