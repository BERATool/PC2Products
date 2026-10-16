"""
GUI test configuration: test data paths and tool parameter values.

The LiDAR tools read the sample tiles in tests/data/LiDAR/. Surface Water Mapping,
Depth-to-Water and Seismic Line Disturbance Analysis read synthetic rasters and
polygons built by the helpers in tests/conftest.py. Outputs go to a temporary
directory created per test session.

Parameter types and labels are read from beratools.json, so they stay in step
with the GUI.
"""

import importlib.util
import json
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1]
TESTDATA_DIR = TESTS_DIR / "data"
TOOLS_JSON = TESTS_DIR.parent / "beratools" / "gui" / "assets" / "beratools.json"


def _load_synthetic_data_helpers():
    """Load tests/conftest.py under another name; tests/pywinauto/conftest.py shadows it."""
    spec = importlib.util.spec_from_file_location("pc2products_test_data", TESTS_DIR / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tools():
    """Return {tool name: [parameter dicts]} for every tool in beratools.json."""
    tools = {}

    def walk(node):
        if isinstance(node, dict):
            if "tool_api" in node and "name" in node:
                tools[node["name"]] = node.get("parameters", [])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    with TOOLS_JSON.open(encoding="utf-8") as f:
        walk(json.load(f))
    return tools


_TOOLS = _load_tools()

# Parameter type lookup from beratools.json (variable -> type info)
PARAM_TYPES = {
    param["variable"]: {"type": param["type"], "subtype": param.get("subtype", "")}
    for params in _TOOLS.values()
    for param in params
}

# Tool-specific parameter labels from beratools.json (tool -> variable -> label)
TOOL_PARAM_LABELS = {
    tool: {param["variable"]: param["label"] for param in params} for tool, params in _TOOLS.items()
}

ALL_TOOL_NAMES = list(_TOOLS)


def make_test_data(testdata_dir, output_dir):
    """Build TEST_DATA dict with resolved paths.

    Args:
        testdata_dir: Path to tests/data/ (holds the LiDAR/ sample tiles).
        output_dir: Path to a temporary output directory for test results; the
            synthetic raster and polygon inputs are written there too.
    """
    helpers = _load_synthetic_data_helpers()
    surface_water = helpers.make_surface_water_data(output_dir / "surface_water_inputs")
    dtw = helpers.make_dtw_data(output_dir / "dtw_inputs")
    seismic = helpers.make_seismic_line_data(output_dir / "seismic_inputs")

    las_folder = str(testdata_dir / "LiDAR")
    raster_output = str(output_dir / "Raster_Output")

    return {
        "LiDAR data info": {
            "in_las_folder": las_folder,
        },
        "Raster Cell size from LiDAR data": {
            "in_las_folder": las_folder,
        },
        "Ground Classify Using CSF": {
            "in_las_folder": las_folder,
            "out_folder": str(output_dir / "Classified_PC"),
            "slope": False,
            "class_threshold": 0.3,
            "cloth_resolution": 1.0,
            "rigidness": 2,
        },
        "Normalize LiDAR Data": {
            "in_las_folder": las_folder,
            "out_folder": str(output_dir / "Normalized_PC"),
            "style": "tin",
        },
        "Generate DTM from LiDAR Data": {
            "in_las_folder": las_folder,
            "out_folder": raster_output,
            "style": "idw",
            "cell_size": 0.5,
        },
        "Generate CHM or DSM from LiDAR Data": {
            "in_las_folder": las_folder,
            "out_folder": raster_output,
            "style": "pitfree",
            "cell_size": 0.5,
        },
        "Detect Hummock and Hollow from LiDAR Data": {
            "in_las_folder": las_folder,
            "out_folder": raster_output,
            "Smooth_by": "median",
            "Min_ws": 3.0,
            "lawn_range": 0.1,
            "cell_size": 0.3,
        },
        "Surface Water Mapping": {
            "in_ortho": {"path": surface_water["ortho"]},
            "in_training": {"path": surface_water["training"], "layer": "training"},
            "out_folder": str(output_dir / "surface_water"),
            "in_chm": {"path": surface_water["chm"]},
            "max_canopy_height": 0.2,
            "min_patch_area": 0.04,
            "points_per_polygon": 20,
            "seed": 1,
            "tile_size": 2000,
        },
        "Depth-to-Water from Surface Water": {
            "in_dtm": {"path": dtw["dtm"]},
            "in_water": {"path": dtw["water"]},
            "out_folder": str(output_dir / "dtw"),
            "in_mask": {"path": dtw["mask"], "layer": "exclude"},
            "grid_size": 10.0,
            "nmax": 10,
            "variogram_model": "Sph",
            "kriging_cell_size": 1.0,
            "tile_size": 1000,
        },
        "Seismic Line Disturbance Analysis": {
            "in_segments": {"path": seismic["segments"], "layer": "segments"},
            "in_dtm": {"path": seismic["dtm"]},
            "in_microform": {"path": seismic["microform"]},
            "out_folder": str(output_dir / "line_analysis"),
            "in_dtw": {"path": seismic["dtw"]},
            "significance": 0.05,
        },
    }
