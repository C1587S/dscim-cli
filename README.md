# dscim-cli

A command-line interface to [dscim](https://github.com/ClimateImpactLab/dscim),
the Climate Impact Lab's social cost of carbon library. It drives both
of dscim's run modes from one YAML config: EPA/RFF (10,000
probabilistic draws over a `runid` dimension, precomputed damage
functions) and discrete SSP/RCP (enumerated scenarios, damage functions
fitted during the run).

Status: working, tested against synthetic fixtures; not yet used
against production-scale data.

## Install

The catalogue, validation, and planning commands need only click and
PyYAML:

```shell
uv pip install .
```

Real runs need dscim and its stack. The `run` extra pins the dscim
`main` commit the test suite runs against:

```shell
uv pip install ".[run]"
```

To use a different dscim, skip the extra and install your version into
the same environment. The CLI warns when the installed dscim is not the
tested commit, and every run writes a `*_run_metadata.yaml` recording
the version, commit, and dependency set that actually produced it.

## First look, no data needed

```shell
dscim-cli stages
```

prints the pipeline: each stage, what it consumes and produces, and
which dimensions it collapses, with dscim source citations. Also
data-free:

```shell
dscim-cli options                     # the full option surface
dscim-cli explain fair_aggregation    # one option in detail
dscim-cli constraints                 # cross-option validity rules
dscim-cli defaults                    # dscim's defaults and what you must set
```

[examples/demo.ipynb](examples/demo.ipynb) walks through everything
below on generated fixtures, no external data required.

## Commands

| Command | What it does |
|---|---|
| `validate CONFIG` | Check a config and report every problem found. |
| `plan CONFIG` | The pipeline for this config as ordered steps, ready or blocked. |
| `run CONFIG` | Execute the configured sweep of menu runs (`--dry-run`, `--resume`). |
| `sum-sectors CONFIG` | Build aggregate sectors (dscim `sum_AMEL`). |
| `reduce CONFIG` | Collapse the batch dimension (dscim `reduce_damages`). |
| `combine CONFIG` | Merge coastal and AMEL damage-function coefficients. |
| `scc CONFIG` | Compose SCCs from uncollapsed run outputs. |
| `stages` | Explain the pipeline and its dimension collapses. |
| `options` | List every dscim option with status and default. |
| `explain OPTION` | Full catalogue record for one option. |
| `constraints` | Cross-option validity rules with citations. |
| `defaults [CONFIG]` | Every effective value and where it came from. |

Every command taking a config accepts `-c KEY=VALUE` overrides (dotted
keys, YAML-parsed values); options can also be set through `DSCIM_CLI_*`
environment variables. Start from
[examples/minimal.yaml](examples/minimal.yaml); the full surface is in
[examples/ssp.yaml](examples/ssp.yaml) and
[examples/rff.yaml](examples/rff.yaml).

## A worked example

```shell
dscim-cli validate config.yml
dscim-cli plan config.yml
dscim-cli run config.yml --dry-run
```

`validate` reports every config problem at once, with the accepted
values and a dscim source citation per error. `plan` shows which steps
are ready and which are blocked on missing files, naming the command
that produces each one. The dry run prints the settings the sweep will
use, marking which values came from the config and which are defaults,
then the expanded runs. Values that select the scientific result (eta,
rho, recipe, discounting, formula, pulse years) must be set explicitly;
dscim's defaults for them are shown by `explain` but never applied
silently.

Then:

```shell
dscim-cli run config.yml --resume
dscim-cli scc config.yml
```

## dscim versions

dscim-cli targets dscim `main` and is tested against the commit pinned
in the `run` extra. Known differences on other branches (reduced-damage
file naming, the regional-SCC surface) are detected where possible and
named in error messages. Not related to `dscim-cil`, the former name of
the dscim-research repository.

## Container

```shell
docker build -t dscim-cli:dev .
docker run --rm -v ./conf:/mnt/conf:ro -v ./data:/mnt/data \
    dscim-cli:dev run /mnt/conf/config.yml
```

## Development

```shell
uv sync --group tests
just validate      # format, lint, test
```

Unit tests run without dscim installed; the integration suite is marked
`integration` and skipped unless dscim is importable.

## License and issues

No license file yet; one will be added before release. Please report
problems through the repository's issue tracker.
