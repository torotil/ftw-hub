# SPDX-FileCopyrightText: 2024-present Roman Zimmermann <roman@more-onion.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pathlib
import sys

import click
import jinja2
import yaml


@click.group
@click.option("--events-yaml", type=click.File(), default=sys.stdin)
@click.pass_context
def cli(ctx, events_yaml):
    """Utility to transform event data into various formats."""
    templates_dir = str(pathlib.Path(__file__).resolve().parent.parent.parent / "templates")
    ctx.obj = {
        "events": yaml.safe_load(events_yaml),
        "jinja_env": jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir), autoescape=True
        ),
    }


@cli.command
@click.pass_context
def monatsuebersicht_html(ctx):
    """Generate a HTML email with a month’s events."""
    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.html")
    click.echo(template.render(ctx.obj["events"]), nl=False)
