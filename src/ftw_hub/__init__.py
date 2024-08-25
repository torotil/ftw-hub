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

from ftw_hub import utils


@click.group
@click.option("--data-dir", type=click.Path(readable=True, file_okay=False, path_type=pathlib.Path))
@click.pass_context
def cli(ctx, data_dir: pathlib.Path):
    """Utility to transform event data into various formats."""
    templates_dir = str(pathlib.Path(__file__).resolve().parent.parent.parent / "templates")
    data = {}
    ctx.obj = {
        "jinja_env": jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir), autoescape=True
        ),
    }
    if data_dir:
        for path in data_dir.rglob("*.yaml"):
            with path.open() as f:
                new_data = yaml.safe_load(f)
                yaml.dump(new_data, sys.stderr)
                data = utils.merge_dicts(data, new_data)
    ctx.obj["data"] = data


link_data = collections.defaultdict(lambda: {"symbol": "link", "alt": "Link-Symbol"})
link_data["fb.event"] = {
    "title": "diese Veranstaltung auf Facebook",
    "symbol": "facebook",
    "alt": "Facebook-Logo",
}
link_data["tradivarium"] = {
    "title": "Veranstaltungsinfos auf tradivarium.at",
    "symbol": "link",
    "alt": "Link-Symbol",
}
link_data["homepage"] = {
    "title": "Mehr Infos auf der Homepage",
    "symbol": "link",
    "alt": "Link-Symbol",
}


def format_event(event: dict, series: dict):
    """Extend the event data structure a bit."""
    if (series_key := event.get("series")) and (event_series := series.get(series_key)):
        event = utils.merge_dicts(event_series.get("defaults", {}), event)
    event["links"] = [{"href": l, **link_data[t]} for t, l in event["links"].items() if l]
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
    data = ctx.obj["data"]

    tpl_data = {
        "events": [],
        "preview": [],
        "workshops": [],
    }
    for event in data["events"]:
        if event["start"] < date_from:
            continue
        key = "preview" if event["start"] >= date_to else "events"
        tpl_data[key].append(format_event(event, data["series"]))
    for event in tpl_data["events"]:
        if ws := event.get("workshop_event", None):
            tpl_data["workshops"].append(ws)

    tpl_data = {k: list(sorted(v, key=lambda e: e["start"])) for k, v in tpl_data.items()}
    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.html")
    click.echo(template.render(tpl_data), nl=False)
