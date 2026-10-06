# Installation

PC2Products runs on BERA Tools, with R and rpy2 added. Both environments below contain only R and
rpy2 on the R side. Every R package comes from CRAN, installed by the tools into the environment's R
the first time they need it (see
[How all the tools behave](../technical/tool_behaviour.md#how-all-the-tools-behave)).

| | `environment.yml` (conda) | `pixi.toml` (pixi) |
|---|---|---|
| Python | 3.12 | 3.14 |
| R | `r-base` 4.5.x | `r-base` 4.5.x |
| rpy2 | From PyPI | From conda-forge on Linux, from PyPI on Windows |
| R packages | None | None |
| Platforms | Any | `win-64`, `linux-64` |

R is held at 4.5.x because conda-forge builds rpy2 for R 4.5 on Linux only, and for nothing newer
than R 4.4 on Windows, which is why rpy2 comes from PyPI on Windows. On Windows, CRAN provides
prebuilt packages for R 4.5. On Linux, CRAN packages such as `sf` and `terra` are compiled from
source, which needs the GDAL, GEOS, PROJ and udunits development libraries (for example
`libgdal-dev libgeos-dev libproj-dev libudunits2-dev` on Ubuntu) and takes a while on the first run.

## Using conda

```bash
git clone https://github.com/appliedgrg/pc2products.git
cd pc2products
conda env create -n PC2Products -f environment.yml
conda activate PC2Products
pip install --no-deps -e .
```

## Using pixi

```bash
pixi install    # also installs beratools in editable mode, plus pytest and the docs tools
pixi run main   # launch the BERA Tools GUI
```

## Verify the installation

To install every R package up front and confirm that they load, run the R environment test:

```bash
python -m pytest tests/test_r_environment.py -v
```

Then list the tools:

```bash
bt list-tools
```

!!! note "Windows"
    Run the tools from an *activated* environment. If you call the environment's `python.exe`
    directly without activating it, GDAL can fail to load its DLLs.

!!! note "Windows: rpy2 with a standard R install"
    If you use R from `C:\Program Files\R` with rpy2 installed by pip, run the tools and the R tests
    from **PowerShell or cmd, not Git Bash**. Under Git Bash, rpy2 3.6 crashes while locating R
    (`IndexError` in `rpy2/situation`), because Git Bash's `sh` makes `R CMD config` return empty
    output instead of failing.

## Requirements

**Python:** `rpy2` and `psutil`, in addition to the core BERA Tools dependencies. The example
workflow also needs `hydra-core`. All three are in `environment.yml` and `pixi.toml`.

**R:** `r-base` 4.5.x. The tools install these packages into it the first time they need them:

| R package | Purpose |
|-----------|---------|
| `lidR` | LAScatalog processing, `rasterize_terrain`, `rasterize_canopy` |
| `rlas` | Reading LAS/LAZ files |
| `future` | Parallel processing of catalogs |
| `terra` | Raster output and mosaicking |
| `sf`, `units` | CRS, area and map-unit reporting |
| `RCSF` | Cloth Simulation Filter for ground classification |
| `gstat` | Kriging interpolation (DTM and water table) |
| `sp`, `raster`, `stars` | Spatial and raster support |
| `ggplot2` | Plots from Seismic Line Disturbance Analysis |
| `rpart` | Decision tree in Surface Water Mapping |

## Remove the environment

```bash
conda activate  # go to the base environment
conda env remove -n PC2Products
```
