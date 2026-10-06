# Overview

## PC2Products

PC2Products processes LiDAR point clouds with R and [lidR](https://r-lidar.github.io/lidRbook/),
called from Python through [rpy2](https://rpy2.github.io/). Every tool can be run from the BERA Tools
GUI, from the `bt` command, or from Python.

## Key Features

- Dataset summary and recommended raster cell size from point density
- Ground classification with the Cloth Simulation Filter (CSF)
- DTM (TIN, IDW, kriging), height normalization, and CHM/DSM (TIN, pit-free)
- Hummock/hollow micro-topography mapping
- Surface water mapping from an orthomosaic, and depth to water by kriging
- Seismic line disturbance statistics, adapted from Chan, Dabros & McDermid (2026)
- Tiled, parallel processing, with merged mosaics of the outputs

## Data Formats & Conventions

- Point clouds: LAS / LAZ, read from a folder as a lidR `LAScatalog`
- Raster: GeoTIFF
- Vector: GeoPackage, given as `file.gpkg|layer`
- Use a projected coordinate system in metres

## PC2Products Tools

| Tool | `bt` subcommand | Details |
|------|-----------------|---------|
| [LiDAR data info](user/las_info.md) | `las_info` | Prints the CRS, extent, density and normalization status of a dataset. |
| [Raster Cell size from LiDAR data](user/cellsize.md) | `cellsize` | Recommends a raster cell size from the point density. |
| [Ground Classify Using CSF](user/gnd_csf.md) | `gnd_csf` | Classifies ground points with the Cloth Simulation Filter. |
| [Generate DTM from LiDAR Data](user/dtm.md) | `dtm` | Builds a bare-earth DTM with TIN, IDW or kriging. |
| [Normalize LiDAR Data](user/normalize.md) | `normalize` | Subtracts the terrain so that Z is height above ground. |
| [Generate CHM or DSM from LiDAR Data](user/chm_dsm.md) | `chm_dsm` | Builds a CHM from normalized data, or a DSM from the original data. |
| [Detect Hummock and Hollow from LiDAR Data](user/hummock_hollow.md) | `hh` | Maps hummocks, hollows and lawns relative to a smoothed terrain. |
| [Surface Water Mapping](user/surface_water.md) | `surface_water` | Classifies surface water from a true-colour orthomosaic. |
| [Depth-to-Water from Surface Water](user/dtw.md) | `dtw` | Kriges a water table from surface water and computes depth to water. |
| [Seismic Line Disturbance Analysis](user/seismic_line_analysis.md) | `line_analysis` | Compares seismic line segments with the surrounding peatland by disturbance class. |
