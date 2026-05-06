"""
tests/test_core/test_widgets.py

Тесты: widgets.py — FilterButton, UserTag, StepperWidget, LogWidget,
MediaButton, ChipButton, SplitModeButton (свойства и внутреннее состояние).
Требует QApplication (PySide6).
"""
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestFilterButton:
    def test_filter_key_property(self, qapp):
        from core.ui_shared.widgets import FilterButton
        btn = FilterButton("All", "all")
        assert btn.filter_key == "all"

    def test_filter_key_custom(self, qapp):
        from core.ui_shared.widgets import FilterButton
        btn = FilterButton("Errors", "error")
        assert btn.filter_key == "error"

    def test_checkable(self, qapp):
        from core.ui_shared.widgets import FilterButton
        btn = FilterButton("All", "all")
        assert btn.isCheckable()


class TestUserTag:
    def test_user_id_property(self, qapp):
        from core.ui_shared.widgets import UserTag
        tag = UserTag("@alice", user_id=42)
        assert tag.user_id == 42

    def test_is_all_false_by_default(self, qapp):
        from core.ui_shared.widgets import UserTag
        tag = UserTag("@bob")
        assert tag.is_all is False

    def test_is_all_true_when_set(self, qapp):
        from core.ui_shared.widgets import UserTag
        tag = UserTag("All", is_all=True)
        assert tag.is_all is True

    def test_text_contains_username(self, qapp):
        from core.ui_shared.widgets import UserTag
        tag = UserTag("@alice")
        assert "@alice" in tag.text()

    def test_text_contains_check_for_all(self, qapp):
        from core.ui_shared.widgets import UserTag
        tag = UserTag("Все", is_all=True)
        assert "✓" in tag.text()


class TestStepperWidget:
    def test_default_active_index_zero(self, qapp):
        from core.ui_shared.widgets import StepperWidget
        stepper = StepperWidget()
        assert stepper.current_step() == 0

    def test_set_active_changes_step(self, qapp):
        from core.ui_shared.widgets import StepperWidget
        stepper = StepperWidget()
        stepper.set_active(2)
        assert stepper.current_step() == 2

    def test_custom_steps_count(self, qapp):
        from core.ui_shared.widgets import StepperWidget
        stepper = StepperWidget(steps=["A", "B", "C"])
        assert stepper.current_step() == 0


class TestLogWidget:
    def test_append_stores_entry(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append("Hello", "info")
        assert len(log._all_entries) == 1

    def test_append_info_convenience(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append_info("test")
        assert len(log._all_entries) == 1
        assert log._all_entries[0][2] == "info"

    def test_append_error_convenience(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append_error("fail")
        assert log._all_entries[0][2] == "error"

    def test_clear_removes_all_entries(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append("a", "info")
        log.append("b", "info")
        log.append("c", "info")
        log.clear()
        assert len(log._all_entries) == 0

    def test_multiple_levels_stored(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append("info msg", "info")
        log.append("success msg", "success")
        log.append("warning msg", "warning")
        log.append("error msg", "error")
        assert len(log._all_entries) == 4

    def test_log_levels_valid(self, qapp):
        from core.ui_shared.widgets import LogWidget
        assert "info" in LogWidget._LEVEL_COLORS
        assert "success" in LogWidget._LEVEL_COLORS
        assert "warning" in LogWidget._LEVEL_COLORS
        assert "error" in LogWidget._LEVEL_COLORS

    def test_append_stores_timestamp(self, qapp):
        from core.ui_shared.widgets import LogWidget
        log = LogWidget()
        log.append("test", "info")
        ts, text, level = log._all_entries[0]
        assert len(ts) > 0  # timestamp не пустой
        assert text == "test"


class TestMediaButton:
    def test_media_type_property(self, qapp):
        from core.ui_shared.widgets import MediaButton
        btn = MediaButton("X", "Photo", media_type="photo")
        assert btn.media_type == "photo"

    def test_active_by_default(self, qapp):
        from core.ui_shared.widgets import MediaButton
        btn = MediaButton("X", "P")
        assert btn.isActive() is True

    def test_set_active_false(self, qapp):
        from core.ui_shared.widgets import MediaButton
        btn = MediaButton("X", "P")
        btn.setActive(False)
        assert btn.isActive() is False

    def test_inactive_on_init(self, qapp):
        from core.ui_shared.widgets import MediaButton
        btn = MediaButton("X", "P", active=False)
        assert btn.isActive() is False


class TestChipButton:
    def test_media_type_property(self, qapp):
        from core.ui_shared.widgets import ChipButton
        chip = ChipButton("X", "Video", media_type="video")
        assert chip.media_type == "video"

    def test_set_active_toggles(self, qapp):
        from core.ui_shared.widgets import ChipButton
        chip = ChipButton("X", "P", active=True)
        assert chip.isActive() is True
        chip.setActive(False)
        assert chip.isActive() is False
        chip.setActive(True)
        assert chip.isActive() is True

    def test_inactive_on_init(self, qapp):
        from core.ui_shared.widgets import ChipButton
        chip = ChipButton("X", "P", active=False)
        assert chip.isActive() is False


class TestSplitModeButton:
    def test_mode_property(self, qapp):
        from core.ui_shared.widgets import SplitModeButton
        btn = SplitModeButton("X", "Day", mode="day")
        assert btn.mode == "day"

    def test_mode_none(self, qapp):
        from core.ui_shared.widgets import SplitModeButton
        btn = SplitModeButton("X", "Single", mode="none")
        assert btn.mode == "none"
