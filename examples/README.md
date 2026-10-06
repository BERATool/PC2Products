# Full Workflow Example (Hydra)

This folder contains a [Hydra](https://hydra.cc/)-driven example that runs the PC2Products tools in
sequence, from raw LiDAR tiles to raster products:

| Step | Tool | Reads | Writes |
|------|------|-------|--------|
| `las_info` | LiDAR data info | `DATA_DIR` | Console only |
| `cellsize` | Raster Cell size from LiDAR data | `DATA_DIR` | Console only |
| `gnd_csf` | Ground Classify Using CSF | `DATA_DIR` | `CLASSIFIED_DIR` |
| `dtm` | Generate DTM from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |
| `chm_dsm` | Generate CHM or DSM from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |
| `hh` | Detect Hummock and Hollow from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |

Steps always run in this order. `steps_to_run` only chooses which of them run.

## Files

- `full_workflow.py`: workflow entrypoint.
- `config.yaml`: Hydra config for folders, step selection and each tool's arguments
  (`args_<step>`).

## Requirements

The PC2Products environment (see [Installation](../README.md#installation)). Both `environment.yml`
and `pixi.toml` include what the workflow needs: `hydra-core` (which brings in `omegaconf`), `rpy2`,
`psutil` and R.

## Configure Input Data

`config.yaml` defines three folders:

| Key | Default | Contents |
|-----|---------|----------|
| `DATA_DIR` | `tests/data/LiDAR` | Input LAS/LAZ tiles |
| `CLASSIFIED_DIR` | `${DATA_DIR}/Classified_PC` | Ground-classified tiles written by `gnd_csf` |
| `RASTER_DIR` | `${DATA_DIR}/Raster_Output` | DTM, CHM/DSM and hummock/hollow rasters |

The defaults point at the sample tiles, so the workflow runs as-is from the repository root.
Relative paths are resolved from the folder you run the script from (`hydra.job.chdir` is `false`).

If your data is already ground-classified, skip `gnd_csf` and point `CLASSIFIED_DIR` at the input
folder:

```bash
python examples/full_workflow.py steps_to_run=[dtm,chm_dsm,hh] CLASSIFIED_DIR=D:/my_data/LiDAR
```

## Run

From the repository root:

```bash
python examples/full_workflow.py
```

Run with Hydra overrides:

```bash
python examples/full_workflow.py processes=4
python examples/full_workflow.py steps_to_run=[gnd_csf,dtm]
python examples/full_workflow.py DATA_DIR=D:/my_data/LiDAR
```

## Common Overrides

- `processes=<int>`: number of worker processes. `null` (the default) uses all CPU cores, and the
  tools then apply their own limits.
- `steps_to_run=[...]`: run only the selected steps. An unknown step name stops the workflow before
  anything runs.
- Any tool argument, for example:

```bash
python examples/full_workflow.py args_dtm.style=kriging
python examples/full_workflow.py args_chm_dsm.style=pitfree
python examples/full_workflow.py args_hh.Min_ws=5.0 args_hh.lawn_range=0.2
python examples/full_workflow.py args_gnd_csf.rigidness=3
```

## Output

With the default `style: tin` and `Smooth_by: median`, `Min_ws: 3.0`:

- `CLASSIFIED_DIR`: `<tile>_gnd_classified.las` for each input tile.
- `RASTER_DIR`:
  - `<tile>_gnd_classified_TIN_DTM.tif` and `Merged_TIN_DTM.tif`
  - `<tile>_gnd_classified_TIN_DSM.tif` and `Merged_TIN_DSM.tif` (`_CHM` instead of `_DSM` if the
    data is height-normalized)
  - `CHH_<tile>_gnd_classified_median_3m.tif`, `HH_<tile>_gnd_classified_median_3m.tif`,
    `Merged_CHH_median_3m.tif` and `Merged_HH_median_3m.tif`

Hydra also writes its run log and resolved config to `outputs/<date>/<time>/` in the current folder.
