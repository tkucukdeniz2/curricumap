# Code metadata

SoftwareX code-metadata table for CurricuMap, in the rows of the current SoftwareX template
(the manuscript carries the same table).

| Nr. | Code metadata description | Metadata |
|---|---|---|
| C1 | Current code version | v0.2.0 |
| C2 | Permanent GitHub link to code/repository used for this code version | https://github.com/tkucukdeniz2/curricumap/tree/v0.2.0 (Zenodo archive of all versions: https://doi.org/10.5281/zenodo.22140689) |
| C3 | Legal Code License | MIT |
| C4 | Code versioning system used | git |
| C5 | Software code languages, tools, and services used | Python (≥ 3.10); GitHub Actions CI on Linux (Python 3.10, 3.12, 3.13) and macOS (Python 3.13) plus a wheel-install job; 206 tests, 99% statement coverage |
| C6 | Compilation requirements, operating environments & dependencies | Python ≥ 3.10, tested on Linux and macOS; dependencies declared in `pyproject.toml`: pandas ≥ 2.0, numpy ≥ 1.24, pyyaml ≥ 6.0, jsonschema ≥ 4.0, rapidfuzz ≥ 3.0, openpyxl ≥ 3.1, jinja2 ≥ 3.1; `requirements.txt` pins the versions used for the illustrative example and benchmarks (Python ≥ 3.12), and `validation/requirements.txt` those of the validation |
| C7 | If available Link to developer documentation/manual | https://github.com/tkucukdeniz2/curricumap#readme and https://github.com/tkucukdeniz2/curricumap/blob/v0.2.0/docs/architecture.md |
| C8 | Support email for questions | tkdeniz@iuc.edu.tr |

Install with `pip install .` from a clone of the repository, or with
`pip install "curricumap @ git+https://github.com/tkucukdeniz2/curricumap@v0.2.0"`.
