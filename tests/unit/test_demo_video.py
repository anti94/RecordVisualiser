"""Demo videosu üreticisi — `tools/demo_video.py`.

Bir demo videosunun en tehlikeli hâli, **altyazısının ekrandakinden
farklı bir şey söylemesidir**. Video izleyene tek bir akış olarak gelir;
altyazı "akustik kanalın spektrumu" derken ekranda basınç kanalı
duruyorsa, izleyen bunu doğrulayamaz ve yanlış bilgiyi doğru sanır.

Bu yüzden buradaki testlerin çoğu sahne metinlerini **koddaki
gerçeklerle** karşılaştırır: sözü edilen sekme var mı ve etkin mi,
sözü edilen kanal simülasyon kaynağında var mı, "ikinci Y ekseni"
iddiasını doğrulayacak kadar farklı birimler mi kullanılıyor, ve
spektrumda görüneceği söylenen ton gerçekten Nyquist'in altında mı.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.demo_video import (  # noqa: E402
    ANALYSIS_CHANNEL,
    FIXTURE,
    SCENES,
    SECOND_CHANNEL,
    Scene,
    even_dimension,
    main,
)

# --------------------------------------------------------------------------- #
# SAHNE TANIMLARI
# --------------------------------------------------------------------------- #


def test_there_are_scenes() -> None:
    assert len(SCENES) >= 10


@pytest.mark.parametrize("scene", SCENES, ids=[scene.title for scene in SCENES])
def test_every_scene_says_what_it_shows(scene: Scene) -> None:
    """Başlıksız ya da açıklamasız bir sahne, izleyene hiçbir şey anlatmaz."""
    assert scene.title.strip(), "sahne basligi bos"
    assert len(scene.detail.strip()) >= 25, f"aciklama cok kisa: {scene.detail!r}"
    assert scene.seconds > 0, "sahne suresi pozitif olmali"


def test_the_whole_demo_is_between_thirty_and_a_hundred_and_fifty_seconds() -> None:
    """Otuz saniyenin altı bir şey gösteremez, iki buçuk dakikanın üstü izlenmez."""
    total = sum(scene.seconds for scene in SCENES)

    assert 30.0 <= total <= 150.0, f"toplam sure {total:.1f} s"


def test_the_data_source_switch_is_announced() -> None:
    """Gerçek dosyadan simülasyona geçiş izleyene söylenmeli.

    Söylenmezse video, simülasyon çıktısını gerçek cihaz verisi gibi
    göstermiş olur — bu projenin en pahalı yanlış anlaşılması bu olurdu.
    """
    details = " ".join(scene.detail for scene in SCENES).upper()

    assert "SIMULASYON" in details


def test_the_real_fixture_is_the_first_data_shown() -> None:
    """Demo gerçek bir `.bin` ile başlamalı; sadece sahte veri kandırıcı olur."""
    with_action = [scene for scene in SCENES if scene.action is not None]
    first = with_action[0]

    assert "bin" in first.title.lower()


# --------------------------------------------------------------------------- #
# ALTYAZILAR KODDAKI GERCEKLERLE TUTUYOR MU
# --------------------------------------------------------------------------- #


@pytest.mark.gui
def test_every_tab_the_demo_opens_exists_and_is_enabled() -> None:
    """Sahne metninde geçen her sekme, sekme çubuğunda var ve etkin olmalı."""
    from sonar_analyzer.ui.view_tab_bar import ENABLED_TABS, TAB_TITLES

    mentioned = {
        title
        for title in TAB_TITLES
        if any(title.lower() in scene.title.lower() for scene in SCENES)
    }

    assert mentioned, "hicbir sekmeden soz edilmiyor"
    for title in mentioned:
        assert title in ENABLED_TABS, f"demo pasif sekmeyi aciyor: {title}"


@pytest.mark.gui
def test_the_demo_channels_exist_in_the_simulation_source() -> None:
    """Olmayan bir kanalı açmaya çalışan demo sessizce boş kare çekerdi."""
    from sonar_analyzer.repository.mock_repository import DEFAULT_CHANNELS

    ids = {spec.id for spec in DEFAULT_CHANNELS}

    assert ANALYSIS_CHANNEL in ids
    assert SECOND_CHANNEL in ids


@pytest.mark.gui
def test_the_second_channel_really_has_a_different_unit() -> None:
    """ "İkinci Y ekseni açılır" iddiası ancak birimler farklıysa doğru."""
    from sonar_analyzer.repository.mock_repository import DEFAULT_CHANNELS

    units = {
        spec.id: spec.unit
        for spec in DEFAULT_CHANNELS
        if spec.id in (ANALYSIS_CHANNEL, SECOND_CHANNEL)
    }

    assert units[ANALYSIS_CHANNEL] != units[SECOND_CHANNEL]


@pytest.mark.gui
def test_the_analysis_channel_tone_is_visible_on_the_spectrum_axis() -> None:
    """Asıl kabul: "tonu tepe olarak gorunur" altyazısı doğrulanabilir olmalı.

    Spektrum ekseni 0 Hz - Nyquist arasıdır. Ton Nyquist'in çok altında
    ya da üstündeyse ekranda ya sol kenara yapışır ya hiç çıkmaz; her iki
    hâlde de altyazı yalan söyler.
    """
    from sonar_analyzer.repository.mock_repository import (
        DEFAULT_CHANNELS,
        DEFAULT_SAMPLE_RATE_HZ,
    )

    spec = next(s for s in DEFAULT_CHANNELS if s.id == ANALYSIS_CHANNEL)
    nyquist = DEFAULT_SAMPLE_RATE_HZ / 2.0
    position = spec.frequency_hz / nyquist

    assert 0.10 <= position <= 0.90, (
        f"{spec.frequency_hz} Hz tonu, Nyquist {nyquist} Hz ekseninin "
        f"%{position * 100:.0f} konumunda; kenara yapisik veya eksen disi"
    )


@pytest.mark.gui
def test_the_analysis_channel_is_the_acoustic_one() -> None:
    """Spektral sahneler akustik kanala bağlanmalı; basınç neredeyse saf DC."""
    from sonar_analyzer.repository.mock_repository import DEFAULT_CHANNELS

    spec = next(s for s in DEFAULT_CHANNELS if s.id == ANALYSIS_CHANNEL)

    assert "acoustic" in spec.path.lower()


def test_the_demo_names_the_current_version() -> None:
    """Kapanış altyazısı `VERSION` ile aynı sürümü söylemeli."""
    from sonar_analyzer import __version__

    titles = " ".join(scene.title for scene in SCENES)

    assert __version__ in titles


def test_no_scene_hardcodes_a_stale_number() -> None:
    """Asıl kabul: altyazıya elle yazılan sayı bir sonraki sürümde yanlışa döner.

    Sürüm numarası ve test sayısı gibi değerler videoda kalıcı olarak
    gömülür; kaynağından okunmazlarsa video sessizce yalan söylemeye
    başlar ve bunu kimse fark etmez.
    """
    import re

    from sonar_analyzer import __version__

    for scene in SCENES:
        text = f"{scene.title} {scene.detail}"
        for found in re.findall(r"\b\d+\.\d+\.\d+\b", text):
            assert found == __version__, (
                f"{scene.title!r} sahnesinde elle yazilmis surum {found}; "
                f"guncel surum {__version__}"
            )
        assert not re.search(r"\b\d{4,}\s*test\b", text), (
            f"{scene.title!r} sahnesinde elle yazilmis test sayisi var"
        )


# --------------------------------------------------------------------------- #
# KAYNAKLAR
# --------------------------------------------------------------------------- #


def test_the_fixture_the_demo_opens_is_in_the_repository() -> None:
    assert FIXTURE.is_file(), f"demo var olmayan fixture aciyor: {FIXTURE}"


def test_the_script_is_runnable_and_documents_itself() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "demo_video.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--out" in result.stdout
    assert "--fps" in result.stdout


# --------------------------------------------------------------------------- #
# PARAMETRE DOGRULAMA
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fps", ["0", "61", "-5"])
def test_an_impossible_frame_rate_is_rejected(fps: str) -> None:
    """Sessizce düzeltilen bir parametre, beklenmeyen bir video üretirdi."""
    assert main(["--fps", fps, "--out", "x.mp4"]) == 2


@pytest.mark.parametrize("scale", ["0", "1.5", "-0.2"])
def test_an_impossible_scale_is_rejected(scale: str) -> None:
    assert main(["--scale", scale, "--out", "x.mp4"]) == 2


# --------------------------------------------------------------------------- #
# KARE BOYUTU
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1520, 1520), (1151, 1152), (0, 0), (1, 2), (759, 760)],
)
def test_odd_dimensions_are_rounded_up(value: int, expected: int) -> None:
    """H.264 tek sayı boyut kabul etmez; yuvarlanmazsa ffmpeg düşer."""
    assert even_dimension(value) == expected


@pytest.mark.gui
def test_row_padding_is_stripped_from_the_captured_frame() -> None:
    """Asıl kabul: satır dolgusu atılmazsa görüntü her satırda kayar.

    Genişliği 3'ün katı olmayan bir QImage'da `bytesPerLine`, genişlik×3'ten
    büyüktür. Dolgu ffmpeg'e verilirse video eğrilir; bu sessiz bir bozulma
    olur, çünkü dosya geçerli kalır.
    """
    from PySide6.QtGui import QImage
    from tools.demo_video import image_bytes

    width, height = 5, 3  # 5*3 = 15 bayt/satir -> 16'ya hizalanir
    image = QImage(width, height, QImage.Format.Format_RGB888)
    image.fill(0)

    raw = image_bytes(image)

    assert image.bytesPerLine() > width * 3, "bu boyutta dolgu bekleniyordu"
    assert len(raw) == width * height * 3
