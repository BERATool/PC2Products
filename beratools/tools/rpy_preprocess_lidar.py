import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common
from beratools.utility.spatial_common import decode_file_layer


def rpy_preprocess_lidar(in_las_folder,
            out_folder,
            in_area="",
            max_scan_angle=32.0,
            remove_overlap:bool=True,
            point_density=147.0,
            slope:bool=False,
            class_threshold=0.5,
            cloth_resolution=1.0,
            rigidness=1,
            thin_step=0.1,
            flightline_gap=0.1,
            overlap_step=1.0,
            noise_res=1.0,
            noise_n=20,
            processes=0,
            **kwargs,):
    """Open-source LiDAR preprocessing after Hegels (2023), section 4.5.2 and appendix A.5.

    Replaces her LAStools steps with lidR: clip to the flight areas, remove flight line overlap,
    drop duplicates, classify noise (class 7), homogenize the pulse density, classify the ground
    by cloth simulation and keep only the lowest ground point per thin_step cell. The defaults
    are her settings (32 degree scan angle cutoff, 147 pulses/m², 0.1 m ground thinning, 1 m noise
    voxels with 20 points, 0.1 s flight line gaps); the ground classification uses CSF, as her
    lasground is not open source.
    INPUT: LiDAR folder, output folder, optional flight area polygons, scan angle cutoff,
           overlap removal, pulse density (0 = keep all), CSF parameters, ground thinning step
    returnValue: number of preprocessed LAS files (*_preprocessed.las) written to out_folder
    """
    max_scan_angle = float(max_scan_angle)
    point_density = float(point_density)
    thin_step = float(thin_step)
    if not 0 < max_scan_angle <= 90:
        raise ValueError(f"max_scan_angle must be between 0 and 90 degrees, not {max_scan_angle}")
    if point_density < 0:
        raise ValueError(f"point_density must be 0 (keep all points) or positive, not {point_density}")
    if thin_step <= 0:
        raise ValueError(f"thin_step must be positive, not {thin_step}")
    area_path, area_layer = decode_file_layer(in_area or "")
    area_layer = area_layer or ""  # R gets "" for no layer; rpy2 cannot pass None
    if area_path and not os.path.isfile(area_path):
        raise FileNotFoundError(f"Cannot locate the flight area file: {area_path}")

    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR', 'RCSF', 'rlas', 'future', 'sf', 'data.table']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    print("Checking input parameters....Done")

    rprocesses = r_common.r_processes(processes)

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    preprocess_lidar = r_common.robjects.globalenv['preprocess_lidar']
    n_files = preprocess_lidar(in_las_folder, out_folder, area_path, area_layer, max_scan_angle,
                               bool(remove_overlap), float(flightline_gap), float(overlap_step),
                               float(noise_res), int(noise_n), point_density, bool(slope),
                               float(class_threshold), float(cloth_resolution), int(rigidness),
                               thin_step, rprocesses)
    return int(n_files[0])


if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_preprocess_lidar")

    rpy_preprocess_lidar(**kwargs)

    print('LiDAR preprocessing is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
