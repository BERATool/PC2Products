# Code Testing

PC2Products uses `pytest` to ensure code quality and reliability. This document outlines the tests,
how to run them, and the workflows that run them in CI.

## Test Suite

Sample tiles are in `tests/data/LiDAR/`. The tools write rasters to `tests/data/LiDAR/Raster_Output/`
and point clouds to `tests/data/LiDAR/Classified_PC/` and `tests/data/LiDAR/Normalized_PC/`; all three
are git-ignored. The tests use the arguments in `tests/conftest.py`.

| Tests | What they cover | Needs R |
|-------|-----------------|---------|
| `tests/test_tools.py` | Runs each LiDAR tool on the sample tiles and checks the output | Yes |
| `tests/test_workflow.py` | Runs CSF classification, DTM, DSM, normalization, CHM (from the normalized tiles) and hummock/hollow in sequence on the sample tiles, checking each tool's output, then deletes the outputs | Yes |
| `tests/test_r_environment.py` | Installs any missing R packages the tools need, then checks that they load | Yes |
| `tests/test_surface_water.py` | Runs Surface Water Mapping on a synthetic orthomosaic, CHM and training polygons (built by `make_surface_water_data` in `tests/conftest.py`) | Yes |
| `tests/test_dtw.py` | Runs Depth-to-Water from Surface Water on a synthetic DTM with a known water table (built by `make_dtw_data`) | Yes |
| `tests/test_seismic_line_analysis.py` | Runs Seismic Line Disturbance Analysis on synthetic rasters and segments (built by `make_seismic_line_data`) | Yes |
| `tests/test_cli_entry.py` | `bt` subcommands, argument conversion and rejection of invalid values | No |
| `tests/test_bt_data_validation.py` | Input validation in `BTData` | No |
| `tests/test_bt_data_version.py` | How the app version is resolved from package metadata and git | No |
| `tests/test_pixi_manifest.py` | `pixi.toml` installs `pc2products` (editable) and the docs dependencies | No |
| `tests/pytest_qt/` | GUI forms for each tool, and GUI-to-validation round trips | No |
| `tests/pywinauto/` | Desktop GUI automation (Windows, needs `pywinauto`) | No |

## Running Tests Locally

Activate the environment from [Local Development](development.md#local-development-setup), then run
the tests from the repository root:

=== "All tests"
    Everything except the pywinauto GUI automation:
    ```bash
    python -m pytest tests --ignore=tests/pywinauto
    ```

=== "R tool tests"
    ```bash
    python -m pytest tests/test_tools.py tests/test_r_environment.py -v
    ```

=== "Fast tests (no R)"
    ```bash
    python -m pytest tests/test_cli_entry.py tests/pytest_qt -v
    ```

=== "A test function"
    ```bash
    python -m pytest tests/test_cli_entry.py::test_function_name
    ```

The first run of the R tests installs the R packages into the environment's R, so it can take a while.

!!! note "Windows: rpy2 with a standard R install"
    If you use R from `C:\Program Files\R` with rpy2 installed by pip, run the R tests from
    **PowerShell or cmd, not Git Bash**.

## GitHub Actions

1. **python-integration-tests.yml**: runs on pushes and pull requests to `main` that change
   `beratools/`, `tests/`, `pixi.toml`, `pixi.lock`, `pyproject.toml` or the workflow itself. On
   Ubuntu it sets up the pixi environment and installs the system GDAL/GEOS/PROJ/udunits libraries.
   It then runs `tests/test_r_environment.py`, which compiles and installs the R packages into the
   pixi R, and `tests/test_workflow.py`, both with terminal coverage. The job's timeout is 60 minutes
   to leave room for compiling the R packages.
2. **python-compatibility-tests.yml**: a dispatch-only workflow that runs `tests/test_workflow.py`
   through tox under Python 3.12, 3.13 and 3.14 in micromamba environments.

Coverage is printed in the GitHub Actions job log; it is not uploaded to an external service. Refer
to the [Maintainer Guide](./maintainer.md#actions) for more information on these workflows.

## Write Tests

Tests are required when contributing to PC2Products. Follow these guidelines to keep the test suite
consistent.

### conftest.py

`tests/conftest.py` holds the shared fixtures, the tool arguments used by the tests, and the builders
for synthetic data (`make_surface_water_data`, `make_dtw_data`, `make_seismic_line_data`). Add common
setup code here so that it can be reused across test files.

### Test Organization

Tests are organized in the `tests` directory. A LiDAR tool should have a case in `tests/test_tools.py`
that runs on the sample tiles; a raster tool should have its own test file that builds small synthetic
inputs with a known answer. Use `has_raster_output` and `has_lidar_output` from
`beratools/tools/common.py` to check that a tool wrote its output.

### Naming Conventions

Test files should be named with the prefix `test_` which can be detected by pytest automatically. The test file name should be followed by the module or tool name (e.g., `test_dtw.py`).

### Writing Tests

When writing tests, use assertions to verify that the code behaves as expected. Utilize fixtures from `conftest.py` for setup and cleanup operations.
