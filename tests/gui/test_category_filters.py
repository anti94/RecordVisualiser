"""Channels/Data Tree sekmeleri ve kategori filtreleri — `F3-012`.

Kabul: Sensors, Acoustic, Navigation, Vehicle/Transmission ve BIT
seçimleri doğru çalışır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.data_explorer import CATEGORIES, DataExplorerDock

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    repo = MockRecordingRepository(duration_s=5.0)
    widget.set_recording(repo.metadata(), repo.channels())
    widget.set_recordings([(repo.metadata(), repo.channels())])
    return widget


def test_all_five_category_buttons_exist_and_start_checked(dock: DataExplorerDock) -> None:
    assert set(dock.category_buttons) == set(CATEGORIES)
    assert CATEGORIES == ("Sensors", "Acoustic", "Navigation", "Vehicle/Transmission", "BIT")
    for button in dock.category_buttons.values():
        assert button.isChecked()
    assert dock.enabled_categories() == set(CATEGORIES)


# -- her kategori Channels sekmesinde dogru calisir -------------------------


def test_disabling_sensors_hides_the_five_sensor_channels(dock: DataExplorerDock) -> None:
    dock.category_buttons["Sensors"].setChecked(False)
    assert set(dock.visible_channel_ids()) == {"ch5", "ch6", "ch7"}


def test_disabling_acoustic_hides_the_hydrophone(dock: DataExplorerDock) -> None:
    dock.category_buttons["Acoustic"].setChecked(False)
    assert "ch5" not in dock.visible_channel_ids()
    assert len(dock.visible_channel_ids()) == 7


def test_disabling_navigation_hides_depth(dock: DataExplorerDock) -> None:
    dock.category_buttons["Navigation"].setChecked(False)
    assert "ch6" not in dock.visible_channel_ids()
    assert len(dock.visible_channel_ids()) == 7


def test_disabling_vehicle_transmission_hides_voltage(dock: DataExplorerDock) -> None:
    dock.category_buttons["Vehicle/Transmission"].setChecked(False)
    assert "ch7" not in dock.visible_channel_ids()
    assert len(dock.visible_channel_ids()) == 7


def test_disabling_bit_has_no_effect_on_visible_channels(dock: DataExplorerDock) -> None:
    """Kabul kriteri: BIT seçimi 'doğru çalışır' — burada doğrusu hiçbir
    gerçek kanalın gizlenmemesidir; BIT bir ChannelMetadata kanalı değil."""
    dock.category_buttons["BIT"].setChecked(False)
    assert len(dock.visible_channel_ids()) == 8
    assert dock.enabled_categories() == {
        "Sensors",
        "Acoustic",
        "Navigation",
        "Vehicle/Transmission",
    }


def test_reenabling_a_category_restores_its_channels(dock: DataExplorerDock) -> None:
    dock.category_buttons["Acoustic"].setChecked(False)
    assert "ch5" not in dock.visible_channel_ids()

    dock.category_buttons["Acoustic"].setChecked(True)

    assert "ch5" in dock.visible_channel_ids()
    assert len(dock.visible_channel_ids()) == 8


def test_disabling_multiple_categories_combines(dock: DataExplorerDock) -> None:
    dock.category_buttons["Acoustic"].setChecked(False)
    dock.category_buttons["Navigation"].setChecked(False)

    assert set(dock.visible_channel_ids()) == {"ch0", "ch1", "ch2", "ch3", "ch4", "ch7"}


def test_category_filter_combines_with_text_search(dock: DataExplorerDock) -> None:
    """Kategori kapalıysa metin araması bile o kategoriyi geri getirmez."""
    dock.category_buttons["Sensors"].setChecked(False)
    dock.search.setText("pressure")  # ch0, bir Sensors kanali

    assert dock.visible_channel_ids() == []


def test_disabling_all_categories_shows_the_empty_hint(dock: DataExplorerDock) -> None:
    for button in dock.category_buttons.values():
        button.setChecked(False)

    assert dock.visible_channel_ids() == []
    assert dock.empty_hint.isVisible()


# -- Data Tree sekmesinde de dogru calisir ----------------------------------


def _group_labels(device_item: object) -> list[str]:
    return [
        device_item.child(i).text(0)  # type: ignore[attr-defined]
        for i in range(device_item.childCount())  # type: ignore[attr-defined]
        if not device_item.child(i).isHidden()  # type: ignore[attr-defined]
    ]


def test_data_tree_hides_the_disabled_category_group(dock: DataExplorerDock) -> None:
    dock.category_buttons["Navigation"].setChecked(False)

    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None

    assert "Navigation" not in _group_labels(device_item)


def test_data_tree_vehicle_transmission_group_toggles_by_display_label(
    dock: DataExplorerDock,
) -> None:
    dock.category_buttons["Vehicle/Transmission"].setChecked(False)

    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None

    assert "Vehicle / Transmission" not in _group_labels(device_item)


def test_data_tree_reflects_category_state_for_newly_opened_files(
    qtbot: QtBot, dock: DataExplorerDock
) -> None:
    """Kategori kapalıyken yeni bir dosya açılırsa filtre yine de uygulanır."""
    dock.category_buttons["Acoustic"].setChecked(False)
    repo = MockRecordingRepository(duration_s=2.0)

    dock.set_recordings([(repo.metadata(), repo.channels())])

    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    assert "Acoustic" not in _group_labels(device_item)


def test_data_tree_category_filter_does_not_force_lazy_materialization(
    dock: DataExplorerDock,
) -> None:
    """Kategoriyi kapatmak gizlenmemiş grupların lazy durumunu bozmaz."""
    dock.category_buttons["Navigation"].setChecked(False)

    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    sensors_group = next(
        device_item.child(i)
        for i in range(device_item.childCount())
        if device_item.child(i).text(0) == "Sensors"  # type: ignore[union-attr]
    )
    assert sensors_group is not None
    assert sensors_group.childCount() == 1  # hala yer tutucu, materyalize olmadi
