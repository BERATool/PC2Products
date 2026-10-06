# System Overview

PC2Products runs on the BERA Tools framework, which is organized into clear layers:

- `beratools/tools`: thin tool entry points (`rpy_*.py`) and the R processing (`r_scripts_collection.r`)
- `beratools/core`: shared runtime (constants, logger, `tool_base`)
- `beratools/cli`: the `bt` command
- `beratools/gui`: desktop GUI and parameter widgets
- `beratools/utility`: shared helpers (arguments, environment checks, spatial helpers)

## Design principles

- **Separation of concerns**: Python wrappers stay lightweight; the processing runs in R through rpy2.
- **Single source of tool metadata**: GUI and CLI parameter behavior derives from tool configuration.
- **Consistent execution model**: tools support CLI and GUI call modes with shared runtime behaviors.

## Module responsibilities

- `tools/rpy_*.py`: validate inputs, check R packages, call the tool's R function.
- `tools/r_scripts_collection.r`: LiDAR and raster processing with lidR, terra and gstat.
- `tools/r_interface.py`, `tools/r_common.py`: locate R and connect rpy2.
- `cli/*`: the `bt` subcommands, built from tool metadata.
- `gui/*`: exposes tools and parameters for interactive use.

See also: [Execution Pipeline](execution_pipeline.md)
