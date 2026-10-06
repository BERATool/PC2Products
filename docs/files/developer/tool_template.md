# Tool Template (Reference)

This page points to the examples to start from when writing a tool.

## Recommended reading

- Contributor workflow: [How to Add a New Tool](add_new_tool.md)
- Runtime internals: [Tool Runtime Model](../technical/architecture/tool_runtime_model.md)

## PC2Products tools

`beratools/tools/rpy_find_cellsize.py` is the smallest complete PC2Products tool. It shows:

- calling `configure_r_environment()` before importing `r_common`
- checking the inputs and installing the R packages the tool needs
- converting `processes` to an R worker count with `r_common.r_processes`
- sourcing `r_scripts_collection.r` and calling an R function from `robjects.globalenv`
- metadata-driven argument composition via `compose_tool_kwargs`

## Python-only tools

`beratools/tools/tool_template.py` is the BERA Tools template for a tool written in Python. It
demonstrates:

- a standard tool API pattern with framework args (`processes`, `call_mode`, `log_level`)
- metadata-driven argument composition via `compose_tool_kwargs`
- optional multiprocessing through `execute_multiprocessing`
- separation of lightweight tool wrappers from heavy core logic

## Where to place content

- Put contributor step-by-step instructions in `developer/add_new_tool.md`
- Put architecture/runtime mechanics in `technical/architecture/tool_runtime_model.md`
