import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common
from beratools.utility.spatial_common import decode_file_layer


def rpy_surface_water(in_ortho,
            in_training,
            out_folder,
            in_chm="",
            max_canopy_height=0.2,
            min_patch_area=0.04,
            points_per_polygon=2,
            seed=1,
            processes=0,
            **kwargs,):
    """Map surface water from a true-colour orthomosaic with a decision tree.

    Follows Chan, Dabros & McDermid (2026), Forests 17, 489, section 2.4.
    INPUT: orthomosaic (bands 1-3 red, green, blue), training polygons with a 'class' field
           ('water' plus other classes such as 'ground' and 'shadow'), output folder,
           optional CHM, canopy height mask threshold, minimum water patch area,
           training points per polygon, random seed
    returnValue: surface_water.tif (1 water, 0 not water) and cross-validation tables in out_folder
    """
    training_path, training_layer = decode_file_layer(in_training)
    in_chm = in_chm or ""
    for label, path in (("orthomosaic", in_ortho), ("training polygons", training_path),
                        ("CHM", in_chm)):
        if path and not os.path.isfile(path):
            print(f"Error! Cannot locate the {label} file: {path}")
            exit()
    os.makedirs(out_folder, exist_ok=True)

    packages = ['terra', 'rpart']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    print("Checking input parameters....Done")
    if not in_chm:
        print("No CHM given: cells under canopy are not masked out.")

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    surface_water_map = r_common.robjects.globalenv['surface_water_map']
    surface_water_map(in_ortho, training_path, training_layer, in_chm,
                      float(max_canopy_height), float(min_patch_area),
                      int(points_per_polygon), int(seed), out_folder)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_surface_water")

    rpy_surface_water(**kwargs)

    print('Surface water mapping is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
