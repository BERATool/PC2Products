"""
Unit tests for individual widget types using pytest-qt.

Tests NumericInput, BooleanInput, OptionsInput, and FileSelector
in isolation — each widget is constructed with a minimal param dict
and exercised via set_value / get_value round-trips. The param dicts
are taken from PC2Products tool parameters in beratools.json.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt5.QtCore import Qt

from beratools.gui.tool_widgets import ToolWidgets

pytestmark = pytest.mark.gui_qt

SIGNAL_TIMEOUT = 2000
ALL_TOOL_NAMES = [
    "Generate DTM from LiDAR Data",
    "Generate CHM or DSM from LiDAR Data",
    "LiDAR data info",
    "Raster Cell size from LiDAR data",
    "Detect Hummock and Hollow from LiDAR Data",
    "Ground Classify Using CSF",
    "Normalize LiDAR Data",
    "Surface Water Mapping",
    "Depth-to-Water from Surface Water",
    "Seismic Line Disturbance Analysis",
]


# ---------------------------------------------------------------------------
# NumericInput
# ---------------------------------------------------------------------------


class TestNumericInputInt:
    PARAM = {
        "name": "Nearest observations",
        "description": "Number of nearest water points used for each kriging prediction.",
        "variable": "nmax",
        "parameter_type": ["int"],
        "optional": True,
        "default_value": 10,
    }

    def test_default_value(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        assert w.data_input.value() == 10

    def test_set_and_get(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        w.set_value(20)
        assert w.data_input.value() == 20
        assert w.get_value() == {"nmax": 20}

    def test_set_default_value(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        w.set_value(99)
        w.set_default_value()
        assert w.data_input.value() == 10

    def test_spinbox_type(self, make_numeric_input):
        from PyQt5.QtWidgets import QSpinBox

        w = make_numeric_input(self.PARAM)
        assert isinstance(w.data_input, QSpinBox)


class TestNumericInputFloat:
    PARAM = {
        "name": "Water point grid size",
        "description": "Size (m) of the grid cells; the minimum water elevation in each cell becomes one kriging point.",
        "variable": "grid_size",
        "parameter_type": ["float"],
        "optional": True,
        "default_value": 10.0,
    }

    def test_default_value(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        assert w.data_input.value() == pytest.approx(10.0)

    def test_set_and_get(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        w.set_value(5.5)
        assert w.data_input.value() == pytest.approx(5.5)
        result = w.get_value()
        assert result["grid_size"] == pytest.approx(5.5)

    def test_spinbox_type(self, make_numeric_input):
        from PyQt5.QtWidgets import QDoubleSpinBox

        w = make_numeric_input(self.PARAM)
        assert isinstance(w.data_input, QDoubleSpinBox)

    def test_spinbox_decimals(self, make_numeric_input):
        w = make_numeric_input(self.PARAM)
        assert w.data_input.decimals() == 2


# ---------------------------------------------------------------------------
# BooleanInput
# ---------------------------------------------------------------------------


class TestBooleanInputFromOptionList:
    PARAM = {
        "name": "Steep slopes exists.",
        "description": "If steep slopes exist, set this parameter to TRUE to reduce errors during post-processing.",
        "variable": "slope",
        "parameter_type": {"OptionList": [True, False]},
        "optional": True,
        "default_value": False,
    }

    def test_default_unchecked(self, make_boolean_input):
        w = make_boolean_input(self.PARAM)
        assert w.checkbox.isChecked() is False

    def test_toggle(self, make_boolean_input):
        w = make_boolean_input(self.PARAM)
        w.set_value(False)
        assert w.get_value() == {"slope": False}
        w.set_value(True)
        assert w.get_value() == {"slope": True}


# ---------------------------------------------------------------------------
# OptionsInput
# ---------------------------------------------------------------------------


class TestOptionsInput:
    PARAM = {
        "name": "The rigidness of the cloth",
        "description": "1 is very soft (rugged terrain), 2 is medium and 3 is hard (flat terrain).",
        "variable": "rigidness",
        "parameter_type": {"OptionList": [1, 2, 3]},
        "optional": True,
        "default_value": 1,
        "data_type": ["int"],
    }

    def test_default_selection(self, make_options_input):
        w = make_options_input(self.PARAM)
        assert w.combobox.currentText() == "1"

    def test_set_value(self, make_options_input):
        w = make_options_input(self.PARAM)
        w.set_value("3")
        assert w.combobox.currentText() == "3"

    def test_get_value(self, make_options_input):
        w = make_options_input(self.PARAM)
        w.set_value("2")
        assert w.get_value() == {"rigidness": "2"}

    def test_option_count(self, make_options_input):
        w = make_options_input(self.PARAM)
        assert w.combobox.count() == 3

    def test_set_default_value(self, make_options_input):
        w = make_options_input(self.PARAM)
        w.set_value("3")
        w.set_default_value()
        assert w.combobox.currentText() == "1"

    def test_selection_change_signal(self, make_options_input, qtbot):
        w = make_options_input(self.PARAM)
        w.combobox.setCurrentIndex(2)
        assert w.value == "3"


class TestWidgetSignals:
    def test_numeric_value_changed_signal_payload(self, make_numeric_input, qtbot):
        w = make_numeric_input(TestNumericInputInt.PARAM)

        with qtbot.waitSignal(w.data_input.valueChanged, timeout=SIGNAL_TIMEOUT) as blocker:
            w.data_input.setValue(44)

        assert blocker.args == [44]
        assert w.get_value() == {"nmax": 44}

    def test_options_index_changed_signal_payload(self, make_options_input, qtbot):
        w = make_options_input(TestOptionsInput.PARAM)

        with qtbot.waitSignal(w.combobox.currentIndexChanged, timeout=SIGNAL_TIMEOUT) as blocker:
            w.combobox.setCurrentIndex(2)

        assert blocker.args == [2]
        assert w.get_value() == {"rigidness": "3"}

    def test_file_selector_text_changed_signal_payload(self, make_file_selector, qtbot):
        w = make_file_selector(TestFileSelectorRaster.PARAM)
        updated = "updated.tif"

        with qtbot.waitSignal(w.in_file.textChanged, timeout=SIGNAL_TIMEOUT) as blocker:
            w.in_file.setText(updated)

        assert blocker.args == [updated]
        assert w.get_value() == {"in_dtm": updated}


class TestKeyboardInput:
    @pytest.mark.parametrize("typed, expected", [("0", 0), ("1", 1), ("99", 99)])
    def test_numeric_int_key_clicks_boundary_values(self, make_numeric_input, qtbot, typed, expected):
        w = make_numeric_input(TestNumericInputInt.PARAM)
        editor = w.data_input.lineEdit()

        with qtbot.waitSignal(w.data_input.valueChanged, timeout=SIGNAL_TIMEOUT):
            editor.setFocus()
            qtbot.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
            qtbot.keyClick(editor, Qt.Key_Delete)
            qtbot.keyClicks(editor, typed)
            qtbot.keyClick(editor, Qt.Key_Enter)

        assert w.data_input.value() == expected
        assert w.get_value() == {"nmax": expected}

    @pytest.mark.parametrize("typed, expected", [("0.0", 0.0), ("0.1", 0.1), ("99.9", 99.9)])
    def test_numeric_float_key_clicks_boundary_values(self, make_numeric_input, qtbot, typed, expected):
        w = make_numeric_input(TestNumericInputFloat.PARAM)
        editor = w.data_input.lineEdit()

        with qtbot.waitSignal(w.data_input.valueChanged, timeout=SIGNAL_TIMEOUT):
            editor.setFocus()
            qtbot.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
            qtbot.keyClick(editor, Qt.Key_Delete)
            qtbot.keyClicks(editor, typed)
            qtbot.keyClick(editor, Qt.Key_Enter)

        assert w.data_input.value() == pytest.approx(expected)
        assert w.get_value()["grid_size"] == pytest.approx(expected)

    def test_file_selector_path_key_clicks_updates_value(self, make_file_selector, qtbot):
        w = make_file_selector(TestFileSelectorRaster.PARAM)
        w.in_file.setFocus()

        with qtbot.waitSignal(w.in_file.textChanged, timeout=SIGNAL_TIMEOUT):
            qtbot.keyClicks(w.in_file, "C:/tmp/in_file.tif")

        assert w.in_file.text() == "C:/tmp/in_file.tif"
        assert w.get_value() == {"in_dtm": "C:/tmp/in_file.tif"}


# ---------------------------------------------------------------------------
# FileSelector — raster (non-vector)
# ---------------------------------------------------------------------------


class TestFileSelectorRaster:
    PARAM = {
        "name": "DTM raster",
        "description": "Digital terrain model, e.g. from Generate DTM from LiDAR Data.",
        "variable": "in_dtm",
        "parameter_type": {"ExistingFile": ["raster"]},
        "optional": False,
        "default_value": "",
        "output": False,
    }

    def test_empty_default(self, make_file_selector):
        w = make_file_selector(self.PARAM)
        assert w.in_file.text() == ""


# ---------------------------------------------------------------------------
# FileSelector — vector (gpkg)
# ---------------------------------------------------------------------------


class TestFileSelectorVector:
    PARAM = {
        "name": "Training polygons",
        "description": "Polygons with a 'class' field.",
        "variable": "in_training",
        "parameter_type": {"ExistingFile": "vector|polygon"},
        "optional": False,
        "default_value": "",
        "output": False,
    }

    def test_is_vector_flag(self, make_file_selector):
        w = make_file_selector(self.PARAM)
        assert w.is_vector is True


class _FakeFileDialog:
    def __init__(self, file_names=None, selected_filter=""):
        self._file_names = file_names or []
        self._selected_filter = selected_filter

    def exec_(self):
        return bool(self._file_names)

    def selectedFiles(self):
        return self._file_names

    def selectedNameFilter(self):
        return self._selected_filter


class _FakeBrowseState:
    def __init__(self, last_browse_dir=None):
        self._last_browse_dir = last_browse_dir

    def get_last_browse_dir(self):
        return self._last_browse_dir

    def set_last_browse_dir(self, directory):
        self._last_browse_dir = directory


class TestFileSelectorDialogInteraction:
    RASTER_PARAM = TestFileSelectorRaster.PARAM

    def test_setup_dialog_falls_back_to_home_when_no_saved_dir(self, make_file_selector):
        w = make_file_selector(self.RASTER_PARAM, bt_data_obj=_FakeBrowseState())

        dialog = w.setup_file_dialog(w.get_file_filters())
        assert Path(dialog.directory().absolutePath()) == Path.home()

    def test_select_file_updates_last_browse_dir(self, make_file_selector, qtbot, tmp_path):
        browse_state = _FakeBrowseState()
        raster_dir = tmp_path / "selected"
        raster_dir.mkdir()
        raster = str(raster_dir / "dtm.tif")
        fake_dialog = _FakeFileDialog(
            file_names=[raster],
            selected_filter="Tiff raster files (*.tif *.tiff)",
        )

        w = make_file_selector(self.RASTER_PARAM, bt_data_obj=browse_state)
        with patch.object(w, "setup_file_dialog", return_value=fake_dialog):
            qtbot.mouseClick(w.btn_select, Qt.LeftButton)

        assert browse_state.get_last_browse_dir() == str(raster_dir)

    def test_sequential_selectors_use_latest_browse_dir(self, make_file_selector, qtbot, tmp_path):
        browse_state = _FakeBrowseState()
        first_dir = tmp_path / "first"
        second_start_dir = tmp_path / "older_prefill"
        first_dir.mkdir()
        second_start_dir.mkdir()

        first_selected = str(first_dir / "first.tif")
        fake_dialog = _FakeFileDialog(
            file_names=[first_selected],
            selected_filter="Tiff raster files (*.tif *.tiff)",
        )

        first_selector = make_file_selector(self.RASTER_PARAM, bt_data_obj=browse_state)
        second_selector = make_file_selector(self.RASTER_PARAM, bt_data_obj=browse_state)
        second_selector.set_value(str(second_start_dir / "prefilled.tif"))

        with patch.object(first_selector, "setup_file_dialog", return_value=fake_dialog):
            qtbot.mouseClick(first_selector.btn_select, Qt.LeftButton)

        dialog = second_selector.setup_file_dialog(second_selector.get_file_filters())
        assert Path(dialog.directory().absolutePath()) == first_dir


class TestFileSelectorLayerComboInteraction:
    VECTOR_PARAM = TestFileSelectorVector.PARAM

    def test_vector_gpkg_populates_layer_combo_and_updates_layer(
        self, make_file_selector, patched_layers, qtbot, tmp_path
    ):
        gpkg = str(tmp_path / "input.gpkg")
        Path(gpkg).write_text("", encoding="utf-8")
        patched_layers.return_value = {
            "training": "Polygon",
            "training_2024": "MultiPolygon",
        }

        w = make_file_selector(self.VECTOR_PARAM)
        w.in_file.setText(gpkg)

        qtbot.waitUntil(lambda: not w.layer_combo.isHidden(), timeout=SIGNAL_TIMEOUT)
        assert w.layer_combo.count() >= 2
        assert "training" in w.layer_combo.itemText(0)

        w.layer_combo.setCurrentText("training_2024 (MultiPolygon)")
        assert w.value["layer"] == "training_2024"

    def test_saved_layer_name_restores_when_combo_items_include_geometry_suffix(
        self, make_file_selector, patched_layers, tmp_path
    ):
        gpkg = str(tmp_path / "input.gpkg")
        Path(gpkg).write_text("", encoding="utf-8")
        patched_layers.return_value = {
            "training_site_a": "Polygon",
            "training_site_b": "MultiPolygon",
        }

        param = dict(self.VECTOR_PARAM)
        param["saved_value"] = f"{gpkg}|training_site_b"

        w = make_file_selector(param)

        assert w.value["layer"] == "training_site_b"
        assert w.layer_combo.currentText().startswith("training_site_b")

    @pytest.mark.parametrize(
        ("ext", "expected_visible"),
        [(".gpkg", True), (".shp", False)],
    )
    def test_vector_extensions_show_layer_combo(
        self, make_file_selector, patched_layers, qtbot, tmp_path, ext, expected_visible
    ):
        path = str(tmp_path / f"input{ext}")
        Path(path).write_text("", encoding="utf-8")
        patched_layers.return_value = {"training": "Polygon"}

        w = make_file_selector(self.VECTOR_PARAM)
        w.in_file.setText(path)

        if expected_visible:
            qtbot.waitUntil(lambda: not w.layer_combo.isHidden(), timeout=SIGNAL_TIMEOUT)
            assert w.layer_combo.count() >= 1
        else:
            assert w.layer_combo.isHidden()

    @pytest.mark.parametrize("ext", [".tif", ".tiff", ".img", ".asc"])
    def test_raster_extensions_keep_layer_combo_hidden(self, make_file_selector, ext):
        w = make_file_selector(TestFileSelectorRaster.PARAM)
        w.set_value(f"dummy{ext}")

        assert w.layer_combo.isHidden()

    def test_geojson_keeps_layer_combo_hidden_current_behavior(self, make_file_selector):
        w = make_file_selector(self.VECTOR_PARAM)
        w.in_file.setText("input.geojson")

        assert w.layer_combo.isHidden()

    def test_gpkg_filters_layers_by_restricted_geometry(
        self, make_file_selector, patched_layers, qtbot, tmp_path
    ):
        gpkg = str(tmp_path / "input.gpkg")
        Path(gpkg).write_text("", encoding="utf-8")
        patched_layers.return_value = {
            "segments": "Polygon",
            "centerline": "MultiLineString",
        }

        w = make_file_selector(self.VECTOR_PARAM)
        w.in_file.setText(gpkg)

        qtbot.waitUntil(lambda: not w.layer_combo.isHidden(), timeout=SIGNAL_TIMEOUT)
        assert w.layer_combo.count() == 1
        assert "segments" in w.layer_combo.itemText(0)
        assert "centerline" not in w.layer_combo.itemText(0)

    def test_gpkg_no_compatible_layers_blocks_required_input(
        self, make_file_selector, patched_layers, qtbot, tmp_path
    ):
        gpkg = str(tmp_path / "input.gpkg")
        Path(gpkg).write_text("", encoding="utf-8")
        patched_layers.return_value = {"centerline": "MultiLineString"}

        w = make_file_selector(self.VECTOR_PARAM)
        w.in_file.setText(gpkg)

        qtbot.waitUntil(lambda: not w.layer_combo.isHidden(), timeout=SIGNAL_TIMEOUT)
        assert w.layer_combo.itemText(0) == "(No compatible layers)"
        assert "No compatible layers" in w.input_geometry_error
        assert w.get_value()["in_training"] == ""

    def test_shapefile_geometry_mismatch_sets_warning_and_blocks(self, make_file_selector, tmp_path):
        shp = str(tmp_path / "input.shp")
        Path(shp).write_text("", encoding="utf-8")

        w = make_file_selector(self.VECTOR_PARAM)
        with patch("beratools.gui.tool_widgets.pyogrio.read_info") as mock_read_info:
            mock_read_info.return_value = {"geometry_type": "LineString"}
            w.in_file.setText(shp)

        assert "Geometry mismatch" in w.input_geometry_error
        assert w.get_value()["in_training"] == ""

    def test_layer_popup_width_updates_for_longer_names(
        self, make_file_selector, patched_layers, qtbot, tmp_path
    ):
        short_gpkg = str(tmp_path / "short.gpkg")
        long_gpkg = str(tmp_path / "long.gpkg")
        Path(short_gpkg).write_text("", encoding="utf-8")
        Path(long_gpkg).write_text("", encoding="utf-8")

        w = make_file_selector(self.VECTOR_PARAM)

        patched_layers.return_value = {"a": "Polygon"}
        w.in_file.setText(short_gpkg)
        qtbot.waitUntil(lambda: w.layer_combo.count() > 0, timeout=SIGNAL_TIMEOUT)
        short_width = w.layer_combo.view().minimumWidth()

        patched_layers.return_value = {
            "very_long_training_polygon_layer_name_for_testing_popup_width": "Polygon"
        }
        w.in_file.setText(long_gpkg)
        qtbot.waitUntil(
            lambda: "very_long_training_polygon_layer_name" in w.layer_combo.itemText(0),
            timeout=SIGNAL_TIMEOUT,
        )
        long_width = w.layer_combo.view().minimumWidth()

        assert long_width > short_width


# ---------------------------------------------------------------------------
# ToolWidgets — construction and round-trip for all tools
# ---------------------------------------------------------------------------


class TestToolWidgetsConstruction:
    @pytest.mark.parametrize("tool_name", ALL_TOOL_NAMES)
    def test_widget_count_matches_params(self, make_tool_widget, btdata, tool_name):
        tw = make_tool_widget(tool_name)
        expected = len(btdata.get_bera_tool_args(tool_name))
        assert expected > 0, f"'{tool_name}' has no parameters in beratools.json"
        assert len(tw.widget_list) == expected

    @pytest.mark.parametrize("tool_name", ALL_TOOL_NAMES)
    def test_all_widgets_have_variable(self, make_tool_widget, tool_name):
        tw = make_tool_widget(tool_name)
        for w in tw.widget_list:
            assert hasattr(w, "variable")
            assert w.variable

    def test_load_default_args(self, make_tool_widget):
        tw = make_tool_widget("Ground Classify Using CSF")
        for w in tw.widget_list:
            if hasattr(w, "data_input") and w.data_input and hasattr(w, "set_value"):
                w.set_value(999)
        tw.load_default_args()
        for w in tw.widget_list:
            if hasattr(w, "data_input") and w.data_input:
                assert w.data_input.value() != 999


class TestToolWidgetsAdvancedVisibility:
    def test_optional_hidden_when_advanced_off(self, qtbot, btdata):
        args = btdata.get_bera_tool_args("Ground Classify Using CSF")
        tw = ToolWidgets("Ground Classify Using CSF", args, show_advanced=False)
        qtbot.addWidget(tw)
        for w in tw.widget_list:
            if w.optional:
                assert w.isHidden()

    def test_optional_visible_when_advanced_on(self, make_tool_widget):
        tw = make_tool_widget("Ground Classify Using CSF", show_advanced=True)
        for w in tw.widget_list:
            if w.optional:
                assert not w.isHidden()
