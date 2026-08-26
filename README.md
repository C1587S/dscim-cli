# dscim-cli

A command-line interface to [dscim](https://github.com/ClimateImpactLab/dscim),
the Climate Impact Lab's social cost of carbon library. It drives both
of dscim's run modes from one YAML config: EPA/RFF (10,000
probabilistic draws over a `runid` dimension, precomputed damage
functions) and discrete SSP/RCP (enumerated scenarios, damage functions
fitted during the run).

Not yet used against production-scale data.

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

Every run writes a `*_run_metadata.yaml` recording the dscim version and
commit that produced it.

## Try it

No data needed:

```shell
dscim-cli stages                      # the pipeline and its dimension collapses
dscim-cli options                     # the full option surface
dscim-cli explain fair_aggregation    # one option in detail
dscim-cli constraints                 # cross-option validity rules
dscim-cli defaults                    # dscim's defaults and what you must set
```

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/C1587S/dscim-cli/HEAD?labpath=examples%2Fdemo.ipynb)
runs [examples/demo.ipynb](examples/demo.ipynb) on generated fixtures.

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

## Running it

```shell
dscim-cli validate config.yml
dscim-cli plan config.yml
dscim-cli run config.yml --dry-run
dscim-cli run config.yml --resume
dscim-cli scc config.yml
```

Values that select the scientific result (eta, rho, recipe,
discounting, formula, pulse years) must be set explicitly; dscim's
defaults for them are shown by `explain` but never applied silently.

## dscim versions

dscim-cli targets dscim `main`, pinned to the commit in the `run` extra.
Not related to `dscim-cil`, the former name of the dscim-research
repository.

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

Usnit tests run without dscim installed; the integration suite is marked
`integration` and skipped unless dscim is importable.