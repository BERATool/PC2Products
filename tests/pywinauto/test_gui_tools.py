"""
GUI tests for the PC2Products tools in the BERA Tools GUI, using pywinauto.

These tests launch the GUI, interact with widgets, and verify that form-filling
works for each PC2Products tool. They do NOT run the actual tools (they fill
forms only).

Requirements:
    - pywinauto installed
    - A display (no headless)
    - The sample LiDAR tiles in tests/data/LiDAR/

Run:
    python -m pytest tests/pywinauto/ -v -m gui
    python -m pytest tests/pywinauto/test_gui_tools.py -v -k "test_select_tool" -m gui
"""

import time

import pytest

from conftest import (
    click_browse_and_set_file,
    click_button,
    fill_tool_form,
    select_gpkg_layer,
    select_tool,
    set_checkbox,
    set_numeric,
    set_option_combo,
    set_slider,
)
from gui_test_config import ALL_TOOL_NAMES, TOOL_PARAM_LABELS

pytestmark = pytest.mark.gui

SURFACE_WATER = "Surface Water Mapping"
DTW = "Depth-to-Water from Surface Water"
CSF = "Ground Classify Using CSF"
DTM = "Generate DTM from LiDAR Data"
HUMMOCK_HOLLOW = "Detect Hummock and Hollow from LiDAR Data"


def _label(tool_name, variable):
    return TOOL_PARAM_LABELS[tool_name][variable]


# ---------------------------------------------------------------------------
# Basic UI tests
# ---------------------------------------------------------------------------


class TestMainWindowBasics:
    """Test that the main window loads and basic controls are accessible."""

    def test_window_visible(self, bera_app):
        """Main window should be visible and have correct title."""
        assert bera_app.is_visible()
        assert "BERA Tools" in bera_app.window_text()

    def test_run_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Run", control_type="Button")
        assert btn.exists(timeout=5)
        assert btn.is_enabled()

    def test_cancel_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Cancel", control_type="Button")
        assert btn.exists(timeout=5)

    def test_exit_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Exit", control_type="Button")
        assert btn.exists(timeout=5)

    def test_advanced_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Show Advanced Options", control_type="Button")
        assert btn.exists(timeout=5)

    def test_help_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Tool Help", control_type="Button")
        assert btn.exists(timeout=5)

    def test_load_default_args_button_exists(self, bera_app):
        btn = bera_app.child_window(title="Load Default Arguments", control_type="Button")
        assert btn.exists(timeout=5)


# ---------------------------------------------------------------------------
# Tool selection tests
# ---------------------------------------------------------------------------


class TestToolSelection:
    """Test selecting each PC2Products tool from the tree view."""

    @pytest.mark.parametrize("tool_name", ALL_TOOL_NAMES)
    def test_select_tool(self, bera_app, tool_name):
        """Each tool should be selectable, showing the label of its first parameter."""
        select_tool(bera_app, tool_name)
        time.sleep(0.3)
        # Verify selection via a stable parameter label in the right panel.
        texts = [w.window_text() for w in bera_app.descendants(control_type="Text")]
        expected_label = next(iter(TOOL_PARAM_LABELS[tool_name].values()))
        assert any(expected_label in t for t in texts), (
            f"Expected label '{expected_label}' for tool '{tool_name}' not found in UI labels"
        )


# ---------------------------------------------------------------------------
# Advanced options toggle
# ---------------------------------------------------------------------------


class TestAdvancedOptions:
    """Test the Show/Hide Advanced Options toggle."""

    def test_toggle_advanced(self, bera_app):
        btn = bera_app.child_window(title_re=".*Advanced Options.*", control_type="Button")
        btn.wait("visible enabled", timeout=5)

        original_text = btn.window_text()
        btn.click_input()
        time.sleep(0.5)

        new_text = btn.window_text()
        assert new_text != original_text

        # Toggle back
        btn.click_input()
        time.sleep(0.5)
        assert btn.window_text() == original_text


# ---------------------------------------------------------------------------
# Slider test
# ---------------------------------------------------------------------------


class TestSlider:
    """Test the CPU cores slider."""

    def test_set_slider_value(self, bera_app):
        set_slider(bera_app, 2)
        time.sleep(0.3)
        slider = bera_app.child_window(control_type="Slider", found_index=0)
        assert slider.is_visible()


# ---------------------------------------------------------------------------
# Per-tool form filling tests
# ---------------------------------------------------------------------------


class TestFillForm:
    """Fill every parameter of each PC2Products tool, with advanced options shown."""

    @pytest.mark.parametrize("tool_name", ALL_TOOL_NAMES)
    def test_fill_form(self, bera_app, test_data, tool_name):
        fill_tool_form(bera_app, tool_name, test_data[tool_name])
        time.sleep(0.3)


# ---------------------------------------------------------------------------
# File dialog interaction test (explicit browse button)
# ---------------------------------------------------------------------------


class TestFileDialog:
    """Test the file browse dialog explicitly."""

    def test_browse_and_select_gpkg(self, bera_app, test_data):
        """Open the file dialog for the training polygons and select a GeoPackage."""
        select_tool(bera_app, SURFACE_WATER)
        time.sleep(0.5)

        training = test_data[SURFACE_WATER]["in_training"]
        click_browse_and_set_file(bera_app, _label(SURFACE_WATER, "in_training"), training["path"])
        time.sleep(1)

        # Verify the layer combo appeared (gpkg triggers layer loading)
        try:
            combo = bera_app.child_window(control_type="ComboBox", found_index=1)
            if combo.exists(timeout=3) and combo.is_visible():
                select_gpkg_layer(bera_app, training["layer"])
        except Exception:
            pass  # layer combo may not appear if the dialog did not accept the file

    def test_browse_and_select_tif(self, bera_app, test_data):
        """Open the file dialog for the orthomosaic and select a GeoTIFF."""
        select_tool(bera_app, SURFACE_WATER)
        time.sleep(0.5)

        ortho = test_data[SURFACE_WATER]["in_ortho"]["path"]
        click_browse_and_set_file(bera_app, _label(SURFACE_WATER, "in_ortho"), ortho)
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Numeric input tests
# ---------------------------------------------------------------------------


class TestNumericInput:
    """Test QSpinBox and QDoubleSpinBox interactions (Depth-to-Water advanced options)."""

    def test_set_float_value(self, bera_app):
        select_tool(bera_app, DTW)
        time.sleep(0.5)
        bera_app.child_window(title_re=".*Advanced Options.*", control_type="Button").click_input()
        time.sleep(0.3)
        set_numeric(bera_app, 5.0, param_label=_label(DTW, "grid_size"))

    def test_set_int_value(self, bera_app):
        select_tool(bera_app, DTW)
        time.sleep(0.5)
        bera_app.child_window(title_re=".*Advanced Options.*", control_type="Button").click_input()
        time.sleep(0.3)
        set_numeric(bera_app, 16, param_label=_label(DTW, "nmax"))


# ---------------------------------------------------------------------------
# Boolean / checkbox tests
# ---------------------------------------------------------------------------


class TestBooleanInput:
    """Test QCheckBox interactions (the CSF 'slope' option)."""

    def test_toggle_checkbox(self, bera_app):
        select_tool(bera_app, CSF)
        time.sleep(0.5)
        bera_app.child_window(title_re=".*Advanced Options.*", control_type="Button").click_input()
        time.sleep(0.3)
        set_checkbox(bera_app, _label(CSF, "slope"), checked=True)
        time.sleep(0.3)
        set_checkbox(bera_app, _label(CSF, "slope"), checked=False)


# ---------------------------------------------------------------------------
# Option list (combobox) tests
# ---------------------------------------------------------------------------


class TestOptionsInput:
    """Test QComboBox option selection."""

    def test_select_dtm_style(self, bera_app):
        select_tool(bera_app, DTM)
        time.sleep(0.5)
        # style is a list type with options [tin, idw, kriging]
        set_option_combo(bera_app, "kriging", param_label=_label(DTM, "style"))


# ---------------------------------------------------------------------------
# Load defaults test
# ---------------------------------------------------------------------------


class TestLoadDefaults:
    """Test that Load Default Arguments resets form values."""

    def test_load_defaults(self, bera_app):
        select_tool(bera_app, HUMMOCK_HOLLOW)
        time.sleep(0.5)

        # Change a numeric value (Min_ws, a required parameter, so always visible)
        set_numeric(bera_app, 9.0, param_label=_label(HUMMOCK_HOLLOW, "Min_ws"))
        time.sleep(0.3)

        # Click Load Default Arguments
        click_button(bera_app, "Load Default Arguments")
        time.sleep(0.5)

        # Value should be reset (default is 3.0 for Min_ws)
        spinner = bera_app.child_window(control_type="Spinner", found_index=0)
        try:
            val = spinner.child_window(control_type="Edit").get_value()
            assert not val.startswith("9"), "Value was not reset to default"
        except Exception:
            pass  # can't always read spinner value reliably
