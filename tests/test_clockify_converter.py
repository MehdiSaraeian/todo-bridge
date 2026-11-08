"""Tests for the Clockify time report converter."""

import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from src.todo_converter.clockify_converter import ClockifyConverter, is_clockify_csv
from src.todo_converter.converter import TodoConverter

HEADER = (
    "Project;Client;Description;Task;User;Group;Email;Tags;Billable;Start Date;"
    "Start Time;End Date;End Time;Duration (h);Duration (decimal);"
    "Billable Rate (USD);Billable Amount (USD);Date of creation"
)


def _row(
    project: str,
    description: str,
    start_date: str,
    start: str,
    end_date: str,
    end: str,
    duration: str = "",
    tags: str = "",
    task: str = "",
    client: str = "",
) -> str:
    return (
        f"{project};{client};{description};{task};;;;{tags};Yes;{start_date};"
        f"{start};{end_date};{end};{duration};;0.00;0.00;{start_date}"
    )


@pytest.fixture
def write_csv() -> Iterator:
    paths: list[Path] = []

    def _write(lines: list[str], header: str = HEADER) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("\n".join([header, *lines]) + "\n")
        paths.append(Path(f.name))
        return paths[-1]

    yield _write
    for p in paths:
        p.unlink(missing_ok=True)


def _ms(*args: int) -> int:
    return int(datetime(*args).timestamp() * 1000)


def test_groups_entries_and_sums_time_per_day(write_csv) -> None:
    path = write_csv(
        [
            _row("Alpha", "Work A", "06/11/2026", "10:00:00", "06/11/2026", "11:00:00"),
            _row("Alpha", "Work A", "06/11/2026", "13:00:00", "06/11/2026", "13:30:00"),
            _row("Alpha", "Work A", "05/11/2026", "09:00:00", "05/11/2026", "09:15:00"),
            _row("Beta", "Work A", "05/11/2026", "09:00:00", "05/11/2026", "10:00:00"),
            _row("", "Loose", "02/11/2026", "08:00:00", "02/11/2026", "08:45:00"),
        ]
    )
    conv = ClockifyConverter(path)
    conv.parse()

    assert len(conv.tasks) == 3
    work_a = conv.tasks[0]
    assert work_a.title == "Work A"
    assert work_a.projectId == conv.projects["Alpha"].id
    assert work_a.timeSpentOnDay == {
        "2026-11-06": 90 * 60_000,
        "2026-11-05": 15 * 60_000,
    }
    assert work_a.timeSpent == 105 * 60_000
    assert work_a.created == _ms(2026, 11, 5, 9, 0)
    assert work_a.isDone is False

    assert conv.tasks[1].projectId == conv.projects["Beta"].id
    assert conv.tasks[2].projectId == conv.projects["Imported Tasks"].id


def test_work_start_end_in_time_tracking(write_csv) -> None:
    path = write_csv(
        [
            _row("Alpha", "A", "06/11/2026", "13:00:00", "06/11/2026", "14:00:00"),
            _row("Alpha", "B", "06/11/2026", "09:30:00", "06/11/2026", "10:00:00"),
        ]
    )
    conv = ClockifyConverter(path)
    conv.parse()
    data = conv.get_super_productivity_data()

    tracking = data["data"]["timeTracking"]["project"][conv.projects["Alpha"].id]
    assert tracking["2026-11-06"] == {
        "s": _ms(2026, 11, 6, 9, 30),
        "e": _ms(2026, 11, 6, 14, 0),
    }
    project = data["data"]["project"]["entities"][conv.projects["Alpha"].id]
    assert len(project["taskIds"]) == 2


def test_entry_spanning_midnight_is_split(write_csv) -> None:
    path = write_csv(
        [
            _row("P", "Late", "06/11/2026", "23:30:00", "07/11/2026", "00:45:00"),
        ]
    )
    conv = ClockifyConverter(path)
    conv.parse()
    assert conv.tasks[0].timeSpentOnDay == {
        "2026-11-06": 30 * 60_000,
        "2026-11-07": 45 * 60_000,
    }


def test_duration_fallback_when_end_missing(write_csv) -> None:
    path = write_csv([_row("P", "X", "06/11/2026", "10:00:00", "", "", "01:20:30")])
    conv = ClockifyConverter(path)
    conv.parse()
    assert conv.tasks[0].timeSpent == (80 * 60 + 30) * 1000


@pytest.mark.parametrize(
    ("dates", "expected"),
    [
        (["13/11/2026", "01/11/2026"], "DMY"),
        (["11/13/2026", "11/01/2026"], "MDY"),
        (["2026-11-06"], "YMD"),
        (["01/11/2026", "02/11/2026", "06/11/2026"], "DMY"),  # day varies more
        (["11/01/2026", "11/02/2026", "11/06/2026"], "MDY"),
    ],
)
def test_date_order_detection(write_csv, dates: list[str], expected: str) -> None:
    path = write_csv([_row("P", "X", d, "10:00:00", d, "11:00:00") for d in dates])
    conv = ClockifyConverter(path)
    conv.parse()
    assert conv.date_order == expected


def test_explicit_date_order_and_12h_times(write_csv) -> None:
    path = write_csv(
        [
            _row("P", "X", "11/06/2026", "01:00:00 PM", "11/06/2026", "02:30:00 PM"),
        ]
    )
    conv = ClockifyConverter(path, date_order="MDY")
    conv.parse()
    assert conv.tasks[0].timeSpentOnDay == {"2026-11-06": 90 * 60_000}


def test_tags_task_and_client(write_csv) -> None:
    path = write_csv(
        [
            _row(
                "P",
                "Desc",
                "06/11/2026",
                "10:00:00",
                "06/11/2026",
                "11:00:00",
                tags="dev, urgent",
                task="Sprint 1",
                client="ACME",
            ),
            _row(
                "P",
                "",
                "06/11/2026",
                "12:00:00",
                "06/11/2026",
                "13:00:00",
                task="Only task",
            ),
        ]
    )
    conv = ClockifyConverter(path)
    conv.parse()
    first, second = conv.tasks
    assert sorted(conv.tags[t].title for t in first.tagIds) == ["dev", "urgent"]
    assert first.notes == "Clockify task: Sprint 1\nClient: ACME"
    assert second.title == "Only task"


def test_comma_delimited_export_with_bom(write_csv) -> None:
    header = "﻿" + HEADER.replace(";", ",")
    line = _row("P", "X", "06/11/2026", "10:00:00", "06/11/2026", "11:00:00")
    path = write_csv([line.replace(";", ",")], header=header)
    assert is_clockify_csv(path)
    conv = ClockifyConverter(path)
    conv.parse()
    assert conv.tasks[0].timeSpent == 3_600_000


def test_todo_converter_autodetects_clockify(write_csv) -> None:
    clockify = write_csv(
        [
            _row("P", "X", "06/11/2026", "10:00:00", "06/11/2026", "11:00:00"),
        ]
    )
    plain = write_csv(["Task 1,Work"], header="title,project")
    assert isinstance(TodoConverter(clockify).converter, ClockifyConverter)
    assert not isinstance(TodoConverter(plain).converter, ClockifyConverter)
