"""Tests for the open-source LiDAR preprocessing tool: flight line overlap removal and ground
thinning on synthetic points, and a run on the sample tiles that feeds the LPI tool."""

import os

import pytest

import beratools.tools.r_common as r_common
from beratools.tools.common import has_raster_output, list_files_in_folder
from beratools.tools.rpy_lpi_elai import rpy_lpi_elai
from beratools.tools.rpy_preprocess_lidar import rpy_preprocess_lidar


@pytest.fixture
def r_collection():
    r_common.check_r_packages_installation(["lidR", "RCSF", "rlas", "future", "sf", "data.table"])
    r_common.r["source"](os.path.join(os.path.dirname(r_common.__file__), "r_scripts_collection.r"))
    return r_common.r


def test_overlap_keeps_the_flight_line_at_the_smaller_scan_angle(r_collection):
    # two flight lines 10 s apart: A covers x 0-20 at scan angle 5, B covers x 10-30 at 20;
    # where they overlap (x 10-20) only A stays
    kept_a, kept_b, kept_b_alone = r_collection("""
        library(lidR); library(data.table)
        grid <- CJ(X = seq(0.25, 29.75, 0.5), Y = seq(0.25, 9.75, 0.5))
        a <- grid[X < 20][, `:=`(gpstime = seq(0, 1, length.out = .N), ScanAngleRank = 5L)]
        b <- grid[X > 10][, `:=`(gpstime = seq(10, 11, length.out = .N), ScanAngleRank = 20L)]
        pts <- rbind(a, b)[, `:=`(Z = 0, ReturnNumber = 1L, NumberOfReturns = 1L, Classification = 1L)]
        las <- remove_flightline_overlap(suppressWarnings(LAS(pts)), 0.1, 1)
        c(sum(las$ScanAngleRank == 5L), sum(las$ScanAngleRank == 20L & las$X < 20),
          sum(las$ScanAngleRank == 20L & las$X >= 20))
    """)
    assert kept_a == 40 * 20      # all of A
    assert kept_b == 0            # none of B in the overlap
    assert kept_b_alone == 20 * 20  # B where it is alone


def test_only_the_lowest_ground_point_per_cell_stays_ground(r_collection):
    classes = r_collection("""
        library(lidR); library(data.table)
        pts <- data.table(X = c(0.01, 0.05, 0.09, 0.15), Y = c(0.01, 0.05, 0.09, 0.05),
                          Z = c(0.3, 0.1, 0.2, 0.5), Classification = c(2L, 2L, 2L, 2L),
                          ReturnNumber = 1L, NumberOfReturns = 1L)
        keep_lowest_ground(suppressWarnings(LAS(pts)), 0.1)$Classification
    """)
    # the first three share one 0.1 m cell, of which the second is the lowest; the fourth is alone
    assert list(classes) == [3, 2, 3, 2]


def test_invalid_parameters_rejected(testdata_dir, tmp_path):
    with pytest.raises(ValueError, match="max_scan_angle"):
        rpy_preprocess_lidar(testdata_dir.joinpath("LiDAR").as_posix(), str(tmp_path), max_scan_angle=0)
    with pytest.raises(FileNotFoundError, match="flight area"):
        rpy_preprocess_lidar(testdata_dir.joinpath("LiDAR").as_posix(), str(tmp_path),
                             in_area=str(tmp_path / "missing.gpkg"))


# Integration test: the sample tiles, then the LPI tool on the result
def test_preprocess_then_lpi(testdata_dir, tmp_path, r_collection):
    out_folder = tmp_path / "preprocessed"
    n_files = rpy_preprocess_lidar(testdata_dir.joinpath("LiDAR").as_posix(), out_folder.as_posix())
    assert n_files == 7
    assert len(list(out_folder.glob("*_preprocessed.las"))) == 7

    max_angle, ground, ground_cells = r_collection(f"""
        library(lidR); library(data.table)
        las <- readLAS(list.files("{out_folder.as_posix()}", "\\\\.las$", full.names = TRUE))
        g <- las@data[Classification == 2L]
        c(max(abs(las$ScanAngle)), nrow(g), uniqueN(g[, .(floor(X / 0.1), floor(Y / 0.1))]))
    """)
    assert max_angle <= 32
    assert ground > 0
    assert ground == ground_cells  # at most one ground point per 0.1 m cell

    lpi_folder = tmp_path / "lpi"
    rpy_lpi_elai(out_folder.as_posix(), lpi_folder.as_posix(), cell_size=0.5)
    assert has_raster_output(list_files_in_folder(lpi_folder), "LPI.tif")
