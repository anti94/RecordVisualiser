"""Kayıt klasörü seçicisi — `F7-045`, `F7-051`.

Kabuller: `Open Recording Folder` bir kayıt klasörü seçtirir; dosya
seçimi bozulmadan kalır; klasör bırakıldığında kayıt açılır.

İptal davranışı sözleşmedir ve ayrıca sınanır: diyalog iptal edilirse
**hiçbir sinyal yayılmaz**. İptalde boş bir talep yayılsaydı, açık kayıt
kapanır ve kullanıcı yanlışlıkla oturumunu kaybederdi.

Diyalog dışarıdan verilebilir; testler yerel klasör diyaloğunu açmak
zorunda kalmaz — offscreen Qt'de yerel diyalog sürücülenemez.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from sonar_analyzer.ui.folder_open import (
    FolderOpenController,
    looks_like_recording_folder,
)

pytestmark = pytest.mark.gui


def _recording(root: Path, *, with_tx: bool = True, with_rx: bool = True) -> Path:
    folder = root / "2026-09-12T14-30-00Z"
    folder.mkdir(parents=True)
    if with_tx:
        (folder / "Tx").mkdir()
    if with_rx:
        (folder / "Rx").mkdir()
    return folder


# --------------------------------------------------------------------------- #
# ON ELEME
# --------------------------------------------------------------------------- #


def test_a_folder_with_both_streams_is_recognised(tmp_path: Path) -> None:
    assert looks_like_recording_folder(_recording(tmp_path)) is True


def test_one_stream_is_enough(tmp_path: Path) -> None:
    """Yayın yapılmayan bir oturumda `Tx/` bulunmaz (§2.2)."""
    assert looks_like_recording_folder(_recording(tmp_path, with_tx=False)) is True


def test_a_folder_without_either_stream_is_rejected(tmp_path: Path) -> None:
    plain = tmp_path / "sade"
    plain.mkdir()

    assert looks_like_recording_folder(plain) is False


def test_a_file_is_not_a_recording_folder(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    target.write_bytes(b"x")

    assert looks_like_recording_folder(target) is False


def test_a_missing_path_is_rejected(tmp_path: Path) -> None:
    assert looks_like_recording_folder(tmp_path / "hicyok") is False


# --------------------------------------------------------------------------- #
# F7-045 — DIYALOG
# --------------------------------------------------------------------------- #


def test_choosing_a_folder_emits_a_request(tmp_path: Path) -> None:
    """Asıl kabul: seçilen klasör yükleme talebine dönüşmeli."""
    folder = _recording(tmp_path)
    seen: list[Path] = []
    controller = FolderOpenController(dialog=lambda _parent, _start: str(folder))
    controller.load_requested.connect(seen.append)

    result = controller.request()

    assert result == folder
    assert seen == [folder]


def test_cancelling_emits_nothing(tmp_path: Path) -> None:
    """İptal "boş talep" değildir; hiç talep değildir."""
    seen: list[Path] = []
    rejected: list[str] = []
    controller = FolderOpenController(dialog=lambda _parent, _start: "")
    controller.load_requested.connect(seen.append)
    controller.rejected.connect(rejected.append)

    assert controller.request() is None
    assert seen == []
    assert rejected == []


def test_a_wrong_folder_is_rejected_with_a_reason(tmp_path: Path) -> None:
    """Sessizce yutmak, kullanıcının doğru klasörü seçtiğini sandırırdı."""
    plain = tmp_path / "sade"
    plain.mkdir()
    seen: list[Path] = []
    rejected: list[str] = []
    controller = FolderOpenController(dialog=lambda _parent, _start: str(plain))
    controller.load_requested.connect(seen.append)
    controller.rejected.connect(rejected.append)

    assert controller.request() is None
    assert seen == []
    assert len(rejected) == 1
    assert "Tx/" in rejected[0]


def test_the_start_directory_follows_the_last_choice(tmp_path: Path) -> None:
    """Bir sonraki açılışta aynı yere dönmek, arka arkaya kayıt açmayı kolaylaştırır."""
    folder = _recording(tmp_path)
    controller = FolderOpenController(dialog=lambda _parent, _start: str(folder))

    controller.request()

    assert controller.start_directory == str(folder.parent)


def test_a_rejected_folder_does_not_move_the_start_directory(tmp_path: Path) -> None:
    plain = tmp_path / "sade"
    plain.mkdir()
    controller = FolderOpenController(
        dialog=lambda _parent, _start: str(plain), start_directory="C:/baslangic"
    )

    controller.request()

    assert controller.start_directory == "C:/baslangic"


def test_the_dialog_receives_the_start_directory(tmp_path: Path) -> None:
    folder = _recording(tmp_path)
    seen: list[str] = []

    def dialog(_parent: object, start: str) -> str:
        seen.append(start)
        return str(folder)

    FolderOpenController(dialog=dialog, start_directory="C:/onceki").request()

    assert seen == ["C:/onceki"]


# --------------------------------------------------------------------------- #
# F7-051 — SURUKLE BIRAK
# --------------------------------------------------------------------------- #


def test_a_dropped_folder_opens_the_recording(tmp_path: Path) -> None:
    folder = _recording(tmp_path)
    seen: list[Path] = []
    controller = FolderOpenController()
    controller.load_requested.connect(seen.append)

    assert controller.accept_dropped(folder) is True
    assert seen == [folder]


def test_a_dropped_file_is_left_to_the_file_path(tmp_path: Path) -> None:
    """Asıl kabul: dosya bırakma davranışı bozulmamalı.

    `False` dönmek "bu benim işim değil" demektir; çağıran taraf dosya
    yoluna devam eder.
    """
    target = tmp_path / "kayit.bin"
    target.write_bytes(b"x")
    seen: list[Path] = []
    controller = FolderOpenController()
    controller.load_requested.connect(seen.append)

    assert controller.accept_dropped(target) is False
    assert seen == []


def test_a_dropped_plain_folder_is_not_accepted(tmp_path: Path) -> None:
    plain = tmp_path / "sade"
    plain.mkdir()
    controller = FolderOpenController()

    assert controller.accept_dropped(plain) is False
