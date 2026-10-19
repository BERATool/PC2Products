# How to Add a New Tool

This page focuses on the **practical contributor workflow** for adding a new PC2Products tool. A
PC2Products tool is a thin Python wrapper that validates its inputs and calls an R function through
rpy2.

For runtime internals (CLI/GUI call modes, argument composition, R setup), see:

- [Tool Runtime Model](../technical/architecture/tool_runtime_model.md)
- [How the Tools Run](../technical/tool_behaviour.md)

## 1) Write the R function

Add the processing function to `beratools/tools/r_scripts_collection.r`. Follow the existing
functions: read the input folder as a lidR `LAScatalog`, drop noise with `filter = "-drop_class 7"`,
use `future::plan(multisession)` with the worker count passed in from Python, and call
`mosaic_catalog_outputs` to merge tiled raster outputs.

```r
my_function <- function(in_las_folder, out_folder, rprocesses) {
    ...
}
```

## 2) Create the Python wrapper

Add `beratools/tools/rpy_my_tool.py`. `configure_r_environment()` must run **before** `r_common` is
imported, because it sets up `R_HOME` and the DLL search path that rpy2 needs.
`rpy_find_cellsize.py` is the smallest complete example.

```python
import os

from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


def rpy_my_tool(in_las_folder, out_folder, processes=0, **kwargs):
    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    r_common.check_r_packages_installation(["lidR", "rlas", "future", "terra"])

    rprocesses = r_common.r_processes(processes)

    r_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r_scripts_collection.r")
    r_common.r["source"](r_script)
    r_common.robjects.globalenv["my_function"](in_las_folder, out_folder, rprocesses)


if __name__ == "__main__":
    kwargs = compose_tool_kwargs("rpy_my_tool")
    rpy_my_tool(**kwargs)
```

`check_r_packages_installation` installs any missing R packages from CRAN the first time the tool
runs, so list every package the R function uses.

## 3) Register in GUI metadata

Update `beratools/gui/assets/beratools.json` and add your tool to the `PC2Products` category.

At minimum, define:

- `name`, `info`, `tool_type`, `tool_api`, `icon`, `tech_link`
- parameter list (`variable`, `label`, `description`, `type`, `subtype`, `default`, `output`, `optional`)

`tool_api` must match the module name and the string passed to `compose_tool_kwargs`, or the tool
stops with `Tool API '<name>' not found in beratools.json`.

### Taking part in pipelines

Every registered `python` tool can be a step in a GUI pipeline. To let its inputs be linked to an
earlier step's output, tag the parameters with a *kind*:

- an input parameter gets `"accepts": "<kind>"`;
- an output parameter gets `"produces": {"<kind>": [patterns]}`. An empty list means the output
  folder itself (a folder of point clouds); otherwise the pipeline uses the first glob pattern that
  matches files in the output folder, newest file first.

```json
{"variable": "in_dtm", "accepts": "dtm", ...}
{"variable": "out_folder", "produces": {"dtm": ["Merged_*_DTM.tif", "*_DTM.tif"]}, ...}
```

The kinds in use are `las`, `dtm`, `dsm`, `chm`, `microform`, `water` and `dtw`; add a new one when a
tool writes something new. `tests/test_pipeline.py` checks that every accepted kind has a producer.
For the pipeline to stop when your tool fails, exit with a non-zero code (`sys.exit(1)` or an
uncaught exception), not a plain `exit()`.

## 4) Add the `bt` subcommand

In `beratools/cli/entry.py`:

- add a short alias to `TOOL_ALIASES`, for example `"my_tool": "rpy_my_tool"`
- teach `_resolve_tool_function` to import and return `rpy_my_tool`

`tests/test_cli_entry.py` checks every alias against `beratools.json`, so add the new alias to its
alias list too.

## 5) Test from the CLI first

Run the tool from the command line before validating it in the GUI:

```bash
bt my_tool                                   # show the parameters
bt my_tool --in_las_folder tests/data/LiDAR --out_folder tests/data/LiDAR/Raster_Output
```

Then test it in the GUI once the CLI behavior is stable.

## 6) Add docs and tests

- Add a page under `docs/files/user/`, add it to the Tools section of `nav` in `docs/mkdocs.yml`,
  and add a row to the tool table in `docs/files/overview.md`.
- Add the module to `docs/files/api.md` and to the tool table in
  `docs/files/technical/algorithm_overview.md`.
- Add the tool to the README.
- Add tests in `tests/`, for example a case in `tests/test_tools.py` that runs on the sample tiles.

## 7) Submit a PR

- Follow the branching and contribution guidance in [Development](development.md)
- Request a review and make sure CI passes
