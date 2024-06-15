# SPDX-FileCopyrightText: 2024-present Roman Zimmermann <roman@more-onion.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import collections
import datetime
import pathlib
import sys

import click
import dateutil
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


link_data = collections.defaultdict(lambda: {"symbol": "link", "alt": "Link-Symbol"})
link_data["fb.event"] = {
    "title": "diese Veranstaltung auf Facebook",
    "symbol": "facebook",
    "alt": "Facebook-Logo",
}
link_data["tradivarium"] = {
    "title": "Veranstaltungsinfos auf tradivarium.at",
}


def format_event(event: dict):
    """Extend the event data structure a bit."""
    event["links"] = [{"href": l, **link_data[t]} for t, l in event["links"].items()]
    event["description"] = event["description"].strip()
    return event


@cli.command
@click.argument("month")
@click.pass_context
def monatsuebersicht_html(ctx, month):
    """Generate a HTML email with a month’s events.

    The MONTH must be passed in yyyy-mmm format
    """
    year, month = [int(x) for x in month.split("-")]
    date_from = datetime.datetime(year, month, 1)
    date_to = date_from + dateutil.relativedelta.relativedelta(months=1)
    data = ctx.obj["events"]

    tpl_data = {
        "events": [],
        "preview": [],
    }
    events = []
    preview_events = []
    for event in data["events"]:
        if event["start"] < date_from:
            continue
        key = "preview" if event["end"] > date_to else "events"
        if (series_key := event.get("series")) and (series := data["series"].get(series_key)):
            tpl_data[key].append(format_event({**series.get("defaults", {}), **event}))
    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.html")
    click.echo(template.render(tpl_data), nl=False)
