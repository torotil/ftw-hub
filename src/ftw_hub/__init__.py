# SPDX-FileCopyrightText: 2024-present Roman Zimmermann <roman@more-onion.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import collections
import datetime
import pathlib
import typing as t

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
                data = utils.merge_dicts(data, new_data)
    ctx.obj["data"] = data
    ctx.obj["events"] = list(
        sorted(
            (format_event(e, data.get("series", {})) for e in data.get("events", [])),
            key=lambda e: e["sort_date"],
        )
    )


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
MONTHS_DE = [
    "Jänner",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def format_event(event: dict, series: dict):
    """Extend the event data structure a bit."""
    if (series_key := event.get("series")) and (event_series := series.get(series_key)):
        event = utils.merge_dicts(event_series.get("defaults", {}), event)
    event["links"] = [{"href": l, **link_data[t]} for t, l in event["links"].items() if l]
    event["description"] = event["description"].strip()
    event["sort_date"] = sort_date(event["start"])
    return event


def format_date_range(
    start: datetime.datetime | datetime.date,
    end: t.Optional[datetime.datetime | datetime.date],
    range_word="-",
):
    """Format an event’s start and end time."""
    result = start.strftime("%d.%m.")
    if isinstance(start, datetime.datetime):
        result += " " + start.strftime("%H:%M")
        if end:
            result += f"{range_word}{end.strftime('%H:%M')},"
    else:
        if end and (end > start):
            result += f"{range_word}{end.strftime('%d.%m')}"
    return result


def sort_date(d: datetime.date | datetime.datetime) -> datetime.datetime:
    if isinstance(d, datetime.datetime):
        return d
    return datetime.datetime.combine(d, datetime.datetime.min.time())


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

    tpl_data = {
        "events": [],
        "preview": [],
        "workshops": [],
    }
    for event in ctx.obj["events"]:
        if event["sort_date"] < date_from:
            continue
        key = "preview" if event["sort_date"] >= date_to else "events"
        tpl_data[key].append(event)
    for event in tpl_data["events"]:
        if ws := event.get("workshop_event", None):
            tpl_data["workshops"].append(utils.merge_dicts(event, ws))

    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.html")
    click.echo(template.render(tpl_data), nl=False)


@cli.command
@click.pass_context
def folktanz_at(ctx):
    """Generate a list of events for the folktanz.at website."""
    now = datetime.datetime.now()
    date_from = datetime.datetime(now.year, now.month, 1)

    tpl_data = {
        "events_per_month": collections.defaultdict(list),
        "month_names": {},
        "format_date_range": format_date_range,
    }
    for event in ctx.obj["events"]:
        if sort_date(event["sort_date"]) < date_from:
            continue
        format_date_range(event["start"], event.get("end"))
        month = event["start"].strftime("%y-%m")
        tpl_data["month_names"][
            month
        ] = f"{MONTHS_DE[event['start'].month - 1]} {event['start'].year}"
        tpl_data["events_per_month"][month].append(event)

    template = ctx.obj["jinja_env"].get_template("folktanz-at.html")
    click.echo(template.render(tpl_data), nl=False)
