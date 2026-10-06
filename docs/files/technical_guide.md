# Technical Guide

This section documents **how PC2Products works internally**.

- Use the [User Guide](user_guide.md) for the workflow and each tool's parameters.
- Use the [Developer Guide](developer_guide.md) for contribution and setup.
- Use this Technical Guide for how the tools run, how R is located, and the BERA Tools runtime.

## What is covered

- **Tool overview**: the Python wrappers, the R functions they call, and the shared helpers
- **How the tools run**: input handling, parallel workers, R package installation, tiled output
- **How R is located**: how `R_HOME` and the DLL search path are set before rpy2 is imported
- **Architecture**: the BERA Tools layers, execution pipeline and tool runtime model

## Reading order

1. [Tool Overview](technical/algorithm_overview.md)
2. [How the Tools Run](technical/tool_behaviour.md)
3. Architecture pages
