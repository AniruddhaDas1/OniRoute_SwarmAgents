# Installation

OniRoute requires Python 3.12+, Git, and a local clone. Create a virtual environment and run `python -m pip install -e .`. Contributors and release validators can install all development/build tools with `python -m pip install -e '.[dev]'`. Verify with `oniroute doctor` and `python -m pytest -q`; build with `python -m build`. No database, server, API key, or internet connection is required for metadata, planning, Dry Run, and validation features. Real invocation requires an explicitly configured compatible endpoint.
