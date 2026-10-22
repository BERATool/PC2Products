"""Tests for the Laser Penetration Index and Effective LAI tool: the circular plot sums and the
LPI/eLAI formulas on synthetic return counts, and a run on the sample tiles."""

import math

import numpy
import pytest
import rasterio
from rasterio.transform import from_origin

from beratools.tools.common import has_raster_output, list_files_in_folder
from beratools.tools.rpy_lpi_elai import circle_rows, circle_sum, lpi_elai_rasters, rpy_lpi_elai


def brute_force_circle_sum(values, radius_cells):
    height, width = values.shape
    out = numpy.zeros_like(values, dtype=numpy.int64)
    r = int(math.floor(radius_cells))
    for i in range(height):
        for j in range(width):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= radius_cells ** 2 and 0 <= i + dy < height and 0 <= j + dx < width:
                        out[i, j] += values[i + dy, j + dx]
    return out


@pytest.mark.parametrize("radius_cells", [1.0, 2.5, 4.0, 66.67])
def test_circle_rows_match_the_disc(radius_cells):
    rows = circle_rows(radius_cells)
    cells = sum(2 * dx + 1 for _, dx in rows)
    r = int(math.floor(radius_cells))
    expected = sum(1 for dy in range(-r, r + 1) for dx in range(-r, r + 1)
                   if dx * dx + dy * dy <= radius_cells ** 2)
    assert cells == expected


@pytest.mark.parametrize("radius_cells", [1.0, 2.5, 4.0])
def test_circle_sum_matches_brute_force(radius_cells):
    rng = numpy.random.default_rng(0)
    values = rng.integers(0, 6, size=(23, 31))
    rows = circle_rows(radius_cells)
    r = len(rows) // 2
    padded = numpy.pad(values, r)
    assert numpy.array_equal(circle_sum(padded, rows, values.shape),
                             brute_force_circle_sum(values, radius_cells))


def write_counts(path, total, ground, nodata_mask, cell_size=1.0):
    profile = {"driver": "GTiff", "dtype": "uint32", "count": 2, "nodata": 4294967295,
               "width": total.shape[1], "height": total.shape[0], "crs": "EPSG:3400",
               "transform": from_origin(500000, 6000000, cell_size, cell_size)}
    with rasterio.open(path, "w", **profile) as dst:
        for band, values in ((1, total), (2, ground)):
            values = values.astype("uint32")
            values[nodata_mask] = profile["nodata"]
            dst.write(values, band)


def test_lpi_and_elai_from_counts(tmp_path):
    shape = (40, 40)
    total = numpy.full(shape, 4)
    ground = numpy.full(shape, 1)
    ground[:, 30:] = 0              # no ground returns on the east side
    outside = numpy.zeros(shape, dtype=bool)
    outside[:10, :10] = True        # outside the LiDAR tiles
    counts = tmp_path / "counts.tif"
    write_counts(counts, total, ground, outside)

    out_lpi, out_elai = lpi_elai_rasters(str(counts), str(tmp_path), focal_radius=3.0, max_scan_angle=32.0)
    with rasterio.open(out_lpi) as src:
        lpi = src.read(1)
    with rasterio.open(out_elai) as src:
        elai = src.read(1)

    # every plot fully on the uniform part: 1 of 4 returns is a ground return
    assert lpi[20, 15] == pytest.approx(0.25)
    assert elai[20, 15] == pytest.approx(-math.cos(math.radians(16.0)) / 0.5 * math.log(0.25), rel=1e-6)
    # a plot that holds no ground return: LPI 0, eLAI undefined (ln 0)
    assert lpi[20, 37] == 0 and numpy.isnan(elai[20, 37])
    # no estimate outside the tiles, but cells next to them still get one
    assert numpy.isnan(lpi[:10, :10]).all() and numpy.isnan(elai[:10, :10]).all()
    assert lpi[5, 12] == pytest.approx(0.25)


def test_invalid_parameters_rejected(testdata_dir, tmp_path):
    with pytest.raises(ValueError, match="focal_radius"):
        rpy_lpi_elai(testdata_dir.joinpath("LiDAR").as_posix(), str(tmp_path), focal_radius=0)
    with pytest.raises(ValueError, match="max_scan_angle"):
        rpy_lpi_elai(testdata_dir.joinpath("LiDAR").as_posix(), str(tmp_path), max_scan_angle=200)


# Integration test: R and the sample tiles
def test_rpy_lpi_elai(testdata_dir, tmp_path):
    out_folder = tmp_path / "lpi"
    rpy_lpi_elai(testdata_dir.joinpath("LiDAR").as_posix(), out_folder.as_posix(), cell_size=0.5)

    out_files = list_files_in_folder(out_folder)
    assert has_raster_output(out_files, "LPI.tif") and has_raster_output(out_files, "eLAI.tif")
    with rasterio.open(out_folder / "LPI.tif") as src:
        lpi = src.read(1)
    with rasterio.open(out_folder / "eLAI.tif") as src:
        elai = src.read(1)
    assert numpy.isfinite(lpi).any()
    assert numpy.nanmin(lpi) >= 0 and numpy.nanmax(lpi) <= 1
    assert numpy.nanmin(elai) >= 0


def test_covered_point_density_ignores_empty_bounding_box(testdata_dir, tmp_path):
    """A file covering only half of its bounding box: the density used for the chunk size is
    that of the covered half, not half of it as the bounding box gives."""
    import os
    import beratools.tools.r_common as r_common

    r_common.check_r_packages_installation(["lidR", "rlas", "future", "terra", "sf"])
    r_common.r["source"](os.path.join(os.path.dirname(r_common.__file__), "r_scripts_collection.r"))
    tile = testdata_dir.joinpath("LiDAR", "tile_554600_6138400.las").as_posix()
    folder = (tmp_path / "triangle").as_posix()
    density, bbox_density, true_density = r_common.r(f"""
        library(lidR)
        las <- readLAS("{tile}")
        # keep the triangle below the tile's diagonal: half of the 100 m x 100 m box
        triangle <- filter_poi(las, (X - 554600) + (Y - 6138400) < 100)
        dir.create("{folder}")
        writeLAS(triangle, file.path("{folder}", "triangle.las"))
        ctg <- readLAScatalog("{folder}")
        c(covered_point_density(ctg), npoints(triangle) / as.numeric(sf::st_area(ctg)),
          npoints(triangle) / 5000)
    """)
    assert bbox_density < 0.6 * true_density
    assert 0.85 * true_density < density < 1.25 * true_density


def test_chunked_counts_match_per_file_counts(testdata_dir, tmp_path):
    """Large files are split into chunks; on the sample tiles, forcing chunks of about 50 m must
    give the same LPI as processing each tile whole."""
    import os
    import beratools.tools.r_common as r_common

    las_folder = testdata_dir.joinpath("LiDAR").as_posix()
    r_common.check_r_packages_installation(["lidR", "rlas", "future", "terra", "sf"])
    r_common.r["source"](os.path.join(os.path.dirname(r_common.__file__), "r_scripts_collection.r"))
    lpi_counts = r_common.robjects.globalenv["lpi_counts"]

    lpi = {}
    for name, limits in (("whole", {}), ("chunked", {"max_file_points": 1e5, "chunk_points": 5e4})):
        out_folder = tmp_path / name
        out_folder.mkdir()
        counts = str(lpi_counts(las_folder, out_folder.as_posix(), 0.5, 1.0, False, 2, **limits)[0])
        lpi_path, _ = lpi_elai_rasters(counts, str(out_folder), 10.0, 32.0)
        with rasterio.open(lpi_path) as src:
            lpi[name] = (src.read(1), src.bounds)
    assert len(list((tmp_path / "chunked").glob("*_LPI_counts.tif"))) > 7

    (whole, whole_bounds), (chunked, chunked_bounds) = lpi["whole"], lpi["chunked"]
    assert whole_bounds == chunked_bounds
    both = numpy.isfinite(whole) & numpy.isfinite(chunked)
    assert both.sum() > 0.99 * numpy.isfinite(whole).sum()
    assert numpy.nanmax(numpy.abs(whole[both] - chunked[both])) < 1e-3
