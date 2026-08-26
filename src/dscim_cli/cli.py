"""Command-line entry points."""

import difflib
import importlib
import logging
import os
import sys

import click

from dscim_cli.config import (
    ConfigError,
    apply_overrides,
    apply_selectors,
    effective_settings,
    expand_sweep,
    load_config,
    plan_steps,
    render_plan,
    render_summary,
    settings_summary,
    validate_config,
)
from dscim_cli.options import CATALOGUE, COMPATIBILITY, PIPELINE, REQUIRED, STATUSES

__all__ = ["main"]

_SELECTOR_OPTIONS = (
    click.option("--sector", "sectors", multiple=True, help="Keep only these sectors."),
    click.option(
        "--pulse-year",
        "pulse_years",
        multiple=True,
        type=int,
        help="Keep only these pulse years.",
    ),
    click.option("--recipe", "recipes", multiple=True, help="Keep only these recipes."),
    click.option(
        "--discounting",
        "discountings",
        multiple=True,
        help="Keep only these discounting types.",
    ),
    click.option(
        "--mask",
        "masks",
        multiple=True,
        help="Keep only these ECS masks ('unmasked' for none).",
    ),
    click.option("--eta", type=float, default=None, help="Select one eta/rho pair."),
    click.option("--rho", type=float, default=None, help="Select one eta/rho pair."),
)


def _with_selectors(command):
    for decorator in reversed(_SELECTOR_OPTIONS):
        command = decorator(command)
    return command


_SELECTOR_AXES = {
    "sectors": "sweep.sectors",
    "pulse_years": "sweep.pulse_years",
    "recipes": "sweep.menu_pairs",
    "discountings": "sweep.menu_pairs",
    "masks": "sweep.masks",
    "eta": "sweep.eta_rho",
    "rho": "sweep.eta_rho",
}


def _load(
    config_path: str, overrides: tuple[str, ...], **selectors: object
) -> tuple[dict, dict]:
    config = load_config(config_path)
    sources: dict[str, str] = {}
    if any(v is not None and v != () for v in selectors.values()):
        config = apply_selectors(config, **selectors)  # type: ignore[arg-type]
        for name, value in selectors.items():
            if value is not None and value != ():
                sources[_SELECTOR_AXES[name]] = "flag"
    for raw in overrides:
        key = raw.partition("=")[0]
        sources[key] = "override"
    if overrides:
        config = apply_overrides(config, overrides=list(overrides))
    return config, sources


def _fail(error: ConfigError) -> None:
    for message in error.errors:
        click.echo(f"error: {message}", err=True)
    sys.exit(1)


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "auto_envvar_prefix": "DSCIM_CLI",
    }
)
@click.option("--log-level", default="INFO", show_default=True)
def main(log_level: str) -> None:
    """Command-line interface to the dscim SCC library."""
    logging.basicConfig(level=log_level.upper(), format="%(levelname)s %(message)s")


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
@click.option("--allow-unsupported", is_flag=True)
def validate(
    config_path: str, overrides: tuple[str, ...], allow_unsupported: bool
) -> None:
    """Validate CONFIG_PATH and report every problem found."""
    try:
        config, _ = _load(config_path, overrides)
        warnings = validate_config(config, allow_unsupported=allow_unsupported)
    except ConfigError as error:
        _fail(error)
        return
    for message in warnings:
        click.echo(f"warning: {message}")
    click.echo("config is valid")


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
@click.option("--allow-unsupported", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True, help="Per-run detail in dry-run output.")
@click.option(
    "--runs",
    "run_indices",
    default=None,
    help="Comma-separated 1-based run numbers for per-run detail.",
)
@click.option("--resume", is_flag=True, help="Skip runs whose outputs all exist.")
@_with_selectors
def run(
    config_path: str,
    overrides: tuple[str, ...],
    allow_unsupported: bool,
    dry_run: bool,
    verbose: bool,
    run_indices: str | None,
    resume: bool,
    sectors: tuple[str, ...],
    pulse_years: tuple[int, ...],
    recipes: tuple[str, ...],
    discountings: tuple[str, ...],
    masks: tuple[str, ...],
    eta: float | None,
    rho: float | None,
) -> None:
    """Expand the sweep and execute menu runs.

    Selector flags narrow the config's sweep; a config without a sweep
    block can be driven entirely by flags.
    """
    try:
        config, sources = _load(
            config_path,
            overrides,
            sectors=sectors,
            pulse_years=pulse_years,
            recipes=recipes,
            discountings=discountings,
            masks=masks,
            eta=eta,
            rho=rho,
        )
        warnings = validate_config(config, allow_unsupported=allow_unsupported)
    except ConfigError as error:
        _fail(error)
        return
    for message in warnings:
        click.echo(f"warning: {message}")
    runs = expand_sweep(config)
    click.echo(settings_summary(config, sources=sources, verbose=verbose))

    if dry_run:
        if run_indices is not None:
            indices = [int(part) for part in run_indices.split(",") if part]
            click.echo(render_plan(config, runs, indices=indices))
        elif verbose:
            click.echo(render_plan(config, runs))
        else:
            click.echo(render_summary(config, runs))
        return

    try:
        runner = importlib.import_module("dscim_cli.runner")
    except ModuleNotFoundError as error:
        click.echo(
            f"error: real runs require dscim and its dependencies to be "
            f"installed ({error}); dry-run, validate, plan, and the "
            f"catalogue commands work without them",
            err=True,
        )
        sys.exit(1)
        return
    invocation = " ".join(sys.argv)
    try:
        results = runner.execute(
            config, runs, resume=resume, invocation=invocation, sources=sources
        )
    except runner.PreflightError as error:
        for message in error.errors:
            click.echo(f"error: {message}", err=True)
        sys.exit(1)
        return
    for line in results:
        click.echo(line)


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
@click.option("--allow-unsupported", is_flag=True)
def plan(config_path: str, overrides: tuple[str, ...], allow_unsupported: bool) -> None:
    """Show the whole pipeline for CONFIG_PATH as ordered, statused steps."""
    try:
        config, _ = _load(config_path, overrides)
        validate_config(config, allow_unsupported=allow_unsupported)
    except ConfigError as error:
        _fail(error)
        return
    for index, step in enumerate(plan_steps(config), start=1):
        click.echo(f"{index}. [{step.status()}] {step.title}")
        for entry in step.inputs:
            state = "ok" if os.path.exists(entry.path) else "missing"
            source = f" <- dscim-cli {entry.producer}" if entry.producer else ""
            click.echo(f"     in  [{state}] {entry.path}{source}")
        for path in step.outputs:
            state = "exists" if os.path.exists(path) else "new"
            click.echo(f"     out [{state}] {path}")


@main.command()
def stages() -> None:
    """Explain the pipeline: stages, data flow, and dimension collapses."""
    for index, stage in enumerate(PIPELINE, start=1):
        modes = ",".join(stage.modes)
        click.echo(f"{index}. {stage.name} (modes: {modes})")
        click.echo(f"   {stage.summary}")
        if stage.library_call:
            click.echo(f"   wraps: {stage.library_call}")
        click.echo("   consumes:")
        for item in stage.consumes:
            click.echo(f"     - {item}")
        click.echo("   produces:")
        for item in stage.produces:
            click.echo(f"     - {item}")
        click.echo("   dimensions:")
        for item in stage.collapses:
            click.echo(f"     - {item}")


@main.command(name="options")
@click.option("--stage", default=None, help="Filter by consuming pipeline stage.")
@click.option("--mode", default=None, type=click.Choice(["ssp", "rff"]))
@click.option("--status", default=None, type=click.Choice(list(STATUSES)))
def options_command(stage: str | None, mode: str | None, status: str | None) -> None:
    """List the catalogued dscim option surface."""
    for name, entry in sorted(CATALOGUE.items()):
        if stage and stage not in entry.stages:
            continue
        if mode and mode not in entry.modes:
            continue
        if status and entry.status != status:
            continue
        if entry.config_required:
            default = "required in config"
        elif entry.default is REQUIRED:
            default = "required"
        else:
            default = repr(entry.default)
        stages_label = ",".join(entry.stages) or "-"
        click.echo(
            f"{name:32} {entry.status:12} stages={stages_label:24} default={default}"
        )


@main.command()
@click.argument("option_name")
@click.argument("values", nargs=-1)
def explain(option_name: str, values: tuple[str, ...]) -> None:
    """Show the full catalogue record for OPTION_NAME (and given VALUES)."""
    entry = CATALOGUE.get(option_name)
    if entry is None:
        close = difflib.get_close_matches(option_name, list(CATALOGUE), n=3, cutoff=0.5)
        hint = f"; close matches: {close}" if close else ""
        click.echo(f"error: unknown option {option_name!r}{hint}", err=True)
        sys.exit(1)
    click.echo(f"{entry.name}: {entry.summary}")
    click.echo(f"  status: {entry.status}")
    if entry.reason:
        click.echo(f"  reason: {entry.reason}")
    if entry.restriction:
        click.echo(f"  restriction class: {entry.restriction}")
    click.echo(f"  stages: {', '.join(entry.stages) or '-'}")
    click.echo(f"  modes: {', '.join(entry.modes)}")
    if entry.config_required and entry.default is not REQUIRED:
        click.echo(
            f"  required in config; dscim would default to {entry.default!r} "
            f"if unset, but dscim-cli never applies that silently"
        )
    else:
        click.echo(f"  default: {entry.default!r}")
    click.echo(f"  source: {entry.citation}")
    if entry.values:
        openness = " (open set; known values)" if entry.open_set else ""
        click.echo(f"  values{openness}:")
        wanted = set(values)
        for value in entry.values:
            if wanted and str(value.value) not in wanted:
                continue
            line = f"    {value.value!r}: {value.status}"
            if value.restriction:
                line += f" [{value.restriction}]"
            click.echo(line)
            if value.reason:
                click.echo(f"        {value.reason}")
            if value.citation:
                click.echo(f"        source: {value.citation}")


@main.command()
def constraints() -> None:
    """List the cross-option validity rules."""
    for rule in COMPATIBILITY:
        modes = ",".join(rule.modes)
        click.echo(f"{rule.key} ({rule.kind}; modes: {modes})")
        click.echo(f"  {rule.description}")
        click.echo(f"  source: {rule.citation}")


@main.command()
@click.argument("config_path", type=click.Path(), required=False)
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
def defaults(config_path: str | None, overrides: tuple[str, ...]) -> None:
    """Show every option's effective value and where it came from.

    With CONFIG_PATH, values come from the config where set and from
    dscim's defaults otherwise. Without one, dscim's defaults are shown
    alone.
    """
    if config_path is None:
        rows = effective_settings(None)
    else:
        try:
            config, sources = _load(config_path, overrides)
        except ConfigError as error:
            _fail(error)
            return
        rows = effective_settings(config, sources=sources)
    for name, value, origin in rows:
        rendered = repr(value) if not isinstance(value, str) else value
        click.echo(f"{name:28} {rendered:40} ({origin})")


def _heavy(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        click.echo(
            f"error: this command needs dscim and its dependencies "
            f"installed ({error}); install the 'run' extra",
            err=True,
        )
        sys.exit(1)


def _validated(config_path: str, overrides: tuple[str, ...]) -> dict:
    try:
        config, _ = _load(config_path, overrides)
        validate_config(config)
    except ConfigError as error:
        _fail(error)
        raise SystemExit(1) from None
    return config


@main.command(name="sum-sectors")
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
def sum_sectors(config_path: str, overrides: tuple[str, ...]) -> None:
    """Build the aggregate sectors declared in the aggregates block."""
    config = _validated(config_path, overrides)
    runner = _heavy("dscim_cli.runner")
    for line in runner.sum_sectors(config):
        click.echo(line)


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
def reduce(config_path: str, overrides: tuple[str, ...]) -> None:
    """Collapse the batch dimension per the reduce block."""
    config = _validated(config_path, overrides)
    runner = _heavy("dscim_cli.runner")
    for line in runner.reduce_all(config):
        click.echo(line)


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
def combine(config_path: str, overrides: tuple[str, ...]) -> None:
    """Merge coastal and AMEL coefficients per the combine block."""
    config = _validated(config_path, overrides)
    if "combine" not in config:
        click.echo("error: config has no combine block", err=True)
        sys.exit(1)
    runner = _heavy("dscim_cli.runner")
    for line in runner.combine_all(config):
        click.echo(line)


@main.command()
@click.argument("config_path", type=click.Path())
@click.option("-c", "--conf", "overrides", multiple=True, metavar="KEY=VALUE")
def scc(config_path: str, overrides: tuple[str, ...]) -> None:
    """Compose SCCs from the uncollapsed run outputs per the scc block."""
    config = _validated(config_path, overrides)
    if "scc" not in config:
        click.echo("error: config has no scc block", err=True)
        sys.exit(1)
    composer = _heavy("dscim_cli.scc")
    for line in composer.compose(config):
        click.echo(line)
