"""
Copyright (C) 2025 Applied Geospatial Research Group.

This script is licensed under the GNU General Public License v3.0.
See <https://gnu.org/licenses/gpl-3.0> for full license details.

Author: Maverick Fong

Description:
    This script is helper tools for execute the R scripts.

    Webpage: https://github.com/appliedgrg/beratools

"""

import psutil,os
import subprocess
r = None
robjects = None

# ------------------------------------------------------
# lazy initialization rpy2
# ------------------------------------------------------
def _import_robjects():
    """Import rpy2.robjects without the "'sh' is not recognized" message on Windows.

    On import, rpy2 runs `R CMD config --ldflags` to find R's DLL folders. On Windows that
    command is a shell script that needs sh.exe (from Rtools). Without it, cmd prints
    "'sh' is not recognized as an internal or external command" to stderr; rpy2 catches the
    failure and falls back to R_HOME/bin/x64, so the message is noise. Silence that one call.
    """
    if os.name != "nt":
        import rpy2.robjects as robjects_module
        return robjects_module

    check_output = subprocess.check_output

    def quiet_check_output(cmd, *args, **kwargs):
        if "CMD" in cmd and "config" in cmd:
            kwargs.setdefault("stderr", subprocess.DEVNULL)
        return check_output(cmd, *args, **kwargs)

    subprocess.check_output = quiet_check_output
    try:
        import rpy2.robjects as robjects_module
    finally:
        subprocess.check_output = check_output

    return robjects_module


def initialize_r():
    global r
    global robjects

    if r is not None:
        return

    # Locate R, set up its DLL path and isolate its library before rpy2 starts R,
    # whichever module calls first.
    import beratools.tools.r_interface  # noqa: F401

    robjects_module = _import_robjects()

    robjects = robjects_module
    r = robjects.r

    # quick startup test
    try:
        r_version = str(r("R.version.string")[0])
        print(f"Connected to: {r_version}")
    except Exception as e:
        raise RuntimeError(
        f"R was located but rpy2 could not connect to it:\n{e}"
            )



def r_processes(processes):
    stats = psutil.virtual_memory()  # returns a named tuple
    available = getattr(stats, 'available') / 1024000000
    cpu_count = os.cpu_count() or 1

    # Never ask R for more workers than requested, CPU cores, or 8;
    # parallelly refuses plans that overload the available cores
    if processes <= 0:
        processes = cpu_count
    rprocesses = min(processes, cpu_count, 8)

    if rprocesses > 2:
        if available <= 50:
            rprocesses = 2
        elif available <= 150:
            rprocesses = min(rprocesses, 4)

    return rprocesses

def check_las_files_existence(folder):
    if not os.path.exists(folder):
        print("Error! Cannot locate LiDAR folder, please check.")
        exit()
    else:
        found = False
        for files in os.listdir(folder):
            if files.endswith(".las") or files.endswith(".laz"):
                found = True
                break
        if not found:
            raise FileNotFoundError("Error! Cannot locate input LAS/LAZ file(s), please check!")

def check_las_out_folder_existence(folder):
    if not os.path.exists(folder):
        print("Warning! Cannot locate LiDAR output folder, will be created.")
        os.makedirs(folder, exist_ok=True)


def check_r_packages_installation(packages):
    initialize_r()
    from rpy2.robjects.packages import isinstalled,importr
    from rpy2.robjects import StrVector

    print("Checking R packages....")
    cran_names_to_install = [
        pkg for pkg in packages
        if not isinstalled(pkg)
    ]

    if not cran_names_to_install:
        print("Checking R packages....Done")
        return

    utils = importr('utils')

    utils.chooseCRANmirror(ind=12)  # select the 12th mirror in the list: Canada

    # The environment only provides R itself, so install into that R's own library
    # (not a user library) to keep the packages inside the conda/pixi environment.
    r_lib = str(r('normalizePath(file.path(R.home(), "library"), winslash = "/")')[0])
    print(f"Installing missing R packages into {r_lib}: {', '.join(cran_names_to_install)}")

    need_fasterRaster = False
    if 'fasterRaster' in cran_names_to_install:
        cran_names_to_install.remove('fasterRaster')
        need_fasterRaster = True
    if cran_names_to_install:
        utils.install_packages(StrVector(cran_names_to_install), lib=r_lib)

    if need_fasterRaster:
        devtools=importr('devtools')
        devtools.install_github("adamlilith/fasterRaster", dependencies=True, lib=r_lib)

    still_missing = [pkg for pkg in packages if not isinstalled(pkg)]
    if still_missing:
        raise RuntimeError(
            f"R packages could not be installed into {r_lib}: {', '.join(still_missing)}"
        )

    print("Checking R packages....Done")


def bool2Rbool(value):
    initialize_r()
    from rpy2.robjects import BoolVector
    if isinstance(value, bool):
        return BoolVector([bool(value)])
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "true":
            return BoolVector([True])
        if v == "false":
            return BoolVector([False])
    raise ValueError(
        f"Cannot convert {value!r} ({type(value).__name__}) to R logical"
    )

def float2Rfloat(value):
    initialize_r()
    from rpy2.robjects import FloatVector
    if isinstance(value, (float, int)):
        return FloatVector([float(value)])

    if isinstance(value, str):
        return FloatVector([float(value)])

    raise ValueError(
        f"Cannot convert {value!r} ({type(value).__name__}) to R numeric"
    )
def int2Rint(value):
    initialize_r()
    from rpy2.robjects import IntVector
    if isinstance(value, int):
        return IntVector([value])

    if isinstance(value, str):
        return IntVector([int(value)])

    raise ValueError(
        f"Cannot convert {value!r} ({type(value).__name__}) to R integer"
    )