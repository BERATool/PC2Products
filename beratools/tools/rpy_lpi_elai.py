import time,os,math
import numpy
import rasterio
from rasterio.windows import Window
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


# Output block size (cells per side) for the circular sums; a block plus its plot-radius border
# is read at a time, so memory stays near 100 bytes per cell of the block whatever the area
BLOCK_SIZE = 2048


def circle_rows(radius_cells):
    """Half-widths of the circular plot, one per row offset: the cells (dy, dx) with
    dx^2 + dy^2 <= radius_cells^2, as terra::focalMat(type = "circle") selects them."""
    r = int(math.floor(radius_cells))
    return [(dy, int(math.floor(math.sqrt(max(radius_cells ** 2 - dy * dy, 0.0)))))
            for dy in range(-r, r + 1)]


def circle_sum(padded, rows, shape):
    """Sum of each cell's circular plot. padded holds the block with a border as wide as the
    plot radius on every side. Each row of the circle is one run of cells, summed from a
    running total along the row, so a cell costs one subtraction per row instead of one
    addition per cell of the plot."""
    r = len(rows) // 2
    height, width = shape
    run = numpy.zeros((padded.shape[0], padded.shape[1] + 1), dtype=numpy.int64)
    numpy.cumsum(padded, axis=1, out=run[:, 1:])
    out = numpy.zeros(shape, dtype=numpy.int64)
    for dy, dx in rows:
        band = run[r + dy:r + dy + height]
        out += band[:, r + dx + 1:r + dx + 1 + width] - band[:, r - dx:r - dx + width]
    return out


def lpi_elai_rasters(counts_path, out_folder, focal_radius, max_scan_angle):
    """LPI = ground returns / all returns within the circular plot around each cell, and
    eLAI = -cos(mean scan angle) / 0.5 * ln(LPI), with the mean scan angle half the maximum
    (Hegels 2023, Eq. 6; Richardson et al. 2009). Both are NA outside the LiDAR tiles, where the
    plot holds no return, and eLAI also where the plot holds no ground return (LPI = 0)."""
    out_lpi = os.path.join(out_folder, "LPI.tif")
    out_elai = os.path.join(out_folder, "eLAI.tif")
    elai_factor = math.cos(math.radians(max_scan_angle / 2.0)) / 0.5

    with rasterio.open(counts_path) as src:
        cell_size = abs(src.res[0])
        rows = circle_rows(focal_radius / cell_size)
        r = len(rows) // 2
        profile = {
            "driver": "GTiff", "dtype": "float32", "count": 1, "nodata": float("nan"),
            "width": src.width, "height": src.height, "crs": src.crs, "transform": src.transform,
            "tiled": True, "blockxsize": 512, "blockysize": 512, "compress": "deflate",
            "BIGTIFF": "IF_SAFER",
        }
        blocks = [(row, col) for row in range(0, src.height, BLOCK_SIZE)
                  for col in range(0, src.width, BLOCK_SIZE)]
        print(f"Summing returns within a {focal_radius} m circular plot "
              f"({len(rows)} cells across) over {len(blocks)} block(s)...")

        with rasterio.open(out_lpi, "w", **profile) as dst_lpi, \
                rasterio.open(out_elai, "w", **profile) as dst_elai:
            for step, (row, col) in enumerate(blocks, 1):
                height = min(BLOCK_SIZE, src.height - row)
                width = min(BLOCK_SIZE, src.width - col)
                window = Window(col - r, row - r, width + 2 * r, height + 2 * r)
                counts = src.read((1, 2), window=window, boundless=True, masked=True)
                # cells outside the tiles add no returns and get no estimate
                inside = ~numpy.ma.getmaskarray(counts[0])[r:r + height, r:r + width]
                counts = counts.filled(0)

                total = circle_sum(counts[0], rows, (height, width))
                ground = circle_sum(counts[1], rows, (height, width))
                valid = inside & (total > 0)
                lpi = numpy.full((height, width), numpy.nan, dtype=numpy.float32)
                lpi[valid] = ground[valid] / total[valid]
                elai = numpy.full((height, width), numpy.nan, dtype=numpy.float32)
                with_ground = valid & (ground > 0)
                elai[with_ground] = -elai_factor * numpy.log(lpi[with_ground])
                elai[elai == 0] = 0.0  # -0.0 where LPI = 1

                out_window = Window(col, row, width, height)
                dst_lpi.write(lpi, 1, window=out_window)
                dst_elai.write(elai, 1, window=out_window)
                print(f"R_PROGRESS:{round(50 + 49 * step / len(blocks))}", flush=True)

    print(f"Created {out_lpi} and {out_elai}")
    return out_lpi, out_elai


def rpy_lpi_elai(in_las_folder,
            out_folder,
            cell_size=0.15,
            focal_radius=10.0,
            cut_ht=1.0,
            max_scan_angle=32.0,
            processes=0,
            **kwargs,):
    """Laser penetration index (LPI) and effective leaf area index (eLAI) rasters.

    Follows Hegels (2023), "Characterizing solar radiation on linear disturbances in Alberta's
    boreal forest", MSc thesis, LMU Munich, sections 4.5.2 and 4.6.2. The defaults are the
    thesis settings: 15 cm cells, a 10 m circular plot, returns up to 1 m above the ground
    (the PAR sensor height) as ground returns, and a 32 degree maximum scan angle.
    INPUT: LiDAR folder (ground classified, or already normalized), output folder, cell size
           (0 = from the point density), plot radius, ground return height, maximum scan angle
    returnValue: LPI.tif and eLAI.tif in out_folder, plus the per-tile return counts
                 (*_LPI_counts.tif) and LPI_counts.vrt they are computed from
    """
    cell_size = float(cell_size)
    focal_radius = float(focal_radius)
    cut_ht = float(cut_ht)
    max_scan_angle = float(max_scan_angle)
    if cell_size < 0:
        raise ValueError(f"cell_size must be 0 (from the point density) or positive, not {cell_size}")
    if focal_radius <= 0:
        raise ValueError(f"focal_radius must be positive, not {focal_radius}")
    if cut_ht <= 0:
        raise ValueError(f"cut_ht must be positive, not {cut_ht}")
    if not 0 <= max_scan_angle < 180:
        raise ValueError(f"max_scan_angle must be between 0 and 180 degrees, not {max_scan_angle}")

    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR', 'rlas', 'future', 'terra', 'sf']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    rprocesses = r_common.r_processes(processes)

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    if cell_size == 0.0:
        print("[INFO] No cell size given, the cell size will be estimated from the LiDAR data.")
        results = r_common.robjects.globalenv['pd2cellsize'](in_las_folder, rprocesses)
        cell_size = float(results.rx2("cell_size")[0])
    if focal_radius < cell_size:
        raise ValueError(f"focal_radius ({focal_radius} m) must be at least the cell size ({cell_size} m)")

    is_normalized = bool(r_common.robjects.globalenv['detect_normalized'](in_las_folder)[0])
    if is_normalized:
        print("[INFO]: LiDAR data is normalized, heights are used as they are.")
    else:
        has_ground = r_common.robjects.globalenv['detect_class'](in_las_folder, 2)
        # one TRUE/FALSE per tile, NULL (length 0) for an empty tile
        if not all(bool(tile[0]) for tile in has_ground if len(tile) > 0):
            raise ValueError("Every LiDAR tile needs ground points (class 2) to normalize the heights. "
                             "Classify the ground first, e.g. with Ground Classification (CSF).")
        print("[INFO]: LiDAR data is not normalized, it will be normalized by KNN-IDW.")

    print("Checking input parameters....Done")

    counts_path = r_common.robjects.globalenv['lpi_counts'](
        in_las_folder, out_folder, cell_size, cut_ht, is_normalized, rprocesses)[0]

    return lpi_elai_rasters(str(counts_path), out_folder, focal_radius, max_scan_angle)


if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_lpi_elai")

    rpy_lpi_elai(**kwargs)

    print('LPI and eLAI process is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
