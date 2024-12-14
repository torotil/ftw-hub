# SPDX-FileCopyrightText: 2024-present Roman Zimmermann <roman@more-onion.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import collections
import datetime
import functools
import pathlib
import typing as t

import click
import dateutil
import ics
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
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=jinja2.select_autoescape(["html"], ["txt"]),
        ),
    }
    if data_dir:
        for path in data_dir.rglob("*.yaml"):
            with path.open() as f:
                new_data = yaml.safe_load(f)
                data = utils.merge_dicts(data, new_data)
    ctx.obj["data"] = data
    events = [format_event(e, data.get("series", {})) for e in data.get("events", [])]
    ws_data = {"workshop": True, "social": False, "sub_event": True}
    ws = [
        utils.merge_dicts(e, e["workshop_event"], ws_data) for e in events if "workshop_event" in e
    ]
    ctx.obj["events"] = list(sorted(events + ws, key=lambda e: e["sort_date"]))


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

EVENT_DEFAULTS = {
    "description": "",
    "links": {},
    "workshop": False,
    "social": False,
}


def format_event(event: dict, series: dict):
    """Extend the event data structure a bit."""
    event = utils.merge_dicts(EVENT_DEFAULTS, event)
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
    short=False,
):
    """Format an event’s start and end time."""
    if short and isinstance(start, datetime.datetime):
        start = start.date()
        if end:
            end = end.date()
    result = start.strftime("%d.%m.")
    if isinstance(start, datetime.datetime):
        start_time = start.strftime("%H:%M")
        if end:
            result += f", {start_time}{range_word}{end.strftime('%H:%M')},"
        else:
            result += f" ab {start_time},"
    else:
        if end and (end > start):
            result += f"{range_word}{end.strftime('%d.%m.')},"
        else:
            result += ","
    return result


def sort_date(d: datetime.date | datetime.datetime) -> datetime.datetime:
    """Convert a date to a datetime object."""
    if isinstance(d, datetime.datetime):
        return d
    return datetime.datetime.combine(d, datetime.datetime.min.time())


def generate_ical_url(event: dict):
    """Generate an iCalendar data URL for an event."""
    calender = ics.Calendar()
    ical_event = ics.Event(
        name=event["title"],
        begin=event["start"],
        end=event.get("end"),
        description=event["description"],
    )
    calender.events.add(ical_event)
    return "data:text/calendar;charset=utf-8," + calender.serialize()


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
        "format_date_range": functools.partial(format_date_range, range_word=" bis "),
    }
    for event in ctx.obj["events"]:
        if event["sort_date"] < date_from:
            continue
        if event["sort_date"] >= date_to:
            if not event.get("sub_event", False):
                key = "preview"
            else:
                continue
        else:
            is_workshop = event.get("workshop", False) and not event.get("social", True)
            key = "workshops" if is_workshop else "events"
        event["ical_url"] = generate_ical_url(event)
        tpl_data[key].append(event)

    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.html")
    click.echo(template.render(tpl_data), nl=False)


@cli.command
@click.argument("month")
@click.pass_context
def monatsuebersicht_txt(ctx, month):
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
        "format_date_range": functools.partial(format_date_range, range_word=" bis "),
    }
    for event in ctx.obj["events"]:
        if event["sort_date"] < date_from:
            continue
        if event["sort_date"] >= date_to:
            if not event.get("sub_event", False):
                key = "preview"
            else:
                continue
        else:
            is_workshop = event.get("workshop", False) and not event.get("social", True)
            key = "workshops" if is_workshop else "events"
        tpl_data[key].append(event)

    template = ctx.obj["jinja_env"].get_template("monatsuebersicht.txt")
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
        if event.get("sub_event", False):
            continue
        format_date_range(event["start"], event.get("end"))
        month = event["start"].strftime("%y-%m")
        tpl_data["month_names"][
            month
        ] = f"{MONTHS_DE[event['start'].month - 1]} {event['start'].year}"
        tpl_data["events_per_month"][month].append(event)

    template = ctx.obj["jinja_env"].get_template("folktanz-at.html")
    click.echo(template.render(tpl_data), nl=False)
