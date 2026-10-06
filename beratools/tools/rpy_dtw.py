import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common
from beratools.utility.spatial_common import decode_file_layer



def rpy_dtw(in_dtm,
            in_water,
            out_folder,
            in_mask="",
            grid_size=10.0,
            nmax=10,
            variogram_model="Ste",
            kriging_cell_size=0.0,
            processes=0,
            **kwargs,):
    """Krige a water table from surface water elevations and compute depth-to-water.

    Follows Chan, Dabros & McDermid (2026), Forests 17, 489, section 2.4.
    INPUT: DTM, surface water raster (1 water, e.g. from Surface Water Mapping), output folder,
           optional exclusion polygons, grid size, nearest observations, variogram model,
           kriging cell size (0 = DTM cell size)
    returnValue: water_table.tif and dtw.tif (0 on surface water) in out_folder
    """
    mask_path, mask_layer = decode_file_layer(in_mask or "")
    for label, path in (("DTM", in_dtm), ("surface water", in_water), ("mask", mask_path)):
        if path and not os.path.isfile(path):
            print(f"Error! Cannot locate the {label} file: {path}")
            exit()
    os.makedirs(out_folder, exist_ok=True)

    packages = ['terra', 'gstat']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    print("Checking input parameters....Done")

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    dtw_map = r_common.robjects.globalenv['dtw_map']
    dtw_map(in_dtm, in_water, mask_path, mask_layer, float(grid_size), int(nmax),
            str(variogram_model), float(kriging_cell_size), out_folder)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_dtw")

    rpy_dtw(**kwargs)

    print('Depth-to-water is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
