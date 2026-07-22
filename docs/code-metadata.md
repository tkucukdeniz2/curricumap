# Code metadata

SoftwareX-style code-metadata table for CurricuMap.

| Nr. | Code metadata description | Metadata |
|---|---|---|
| C1 | Current code version | 0.1.0 |
| C2 | Permanent link to code/repository used for this code version | `https://github.com/<org>/curricumap` |
| C3 | Permanent link to reproducible capsule | n/a |
| C4 | Legal code license | MIT |
| C5 | Code versioning system used | git |
| C6 | Software code language used | Python (>=3.10) |
| C7 | Compilation requirements, operating environments & dependencies | Python >=3.10; pandas, numpy, pyyaml, jsonschema, rapidfuzz, openpyxl, jinja2 |
| C8 | If available, link to developer documentation/manual | `README.md` |
| C9 | Support email for questions | tkdeniz@iuc.edu.tr |

## Notes

- **C2**: replace `<org>` with the actual GitHub organization/user once the
  repository is published; this is a placeholder until then.
- **C7**: install with `pip install -e .`, which resolves the dependencies
  above from `pyproject.toml`. Optional development dependency: `pytest>=7.0`.
- **C8**: see `README.md` for the install and quickstart walkthrough
  (`curricumap synth` then `curricumap run`), and `examples/quickstart.md`
  for a standalone copy of the same walkthrough.
