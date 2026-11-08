"""
Clockify converter for time reports.

This module converts a Clockify "Detailed" time report (CSV export) into
Super Productivity JSON format, including the already tracked time and the
projects.

Every Clockify time entry is folded into a Super Productivity task. Entries
that share the same project, Clockify task and description become one task;
their durations are summed up per day into ``timeSpentOnDay`` and in total
into ``timeSpent``. Entries spanning midnight are split across both days.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .base import BaseConverter
from .models import Task, generate_id

# Columns that identify a Clockify detailed report export
CLOCKIFY_SIGNATURE_COLUMNS = {"Project", "Description", "Start Date", "Start Time"}

DEFAULT_PROJECT_NAME = "Imported Tasks"
NO_DESCRIPTION_TITLE = "(no description)"

_DATE_RE = re.compile(r"^\s*(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})\s*$")
_TIME_FORMATS = ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p")


def _read_header(path: Path) -> tuple[list[str], str]:
    """Return the header columns and the delimiter of a CSV file."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        first_line = f.readline()
    delimiter = max((";", ",", "\t"), key=first_line.count)
    header = next(csv.reader([first_line], delimiter=delimiter), [])
    return [col.strip() for col in header], delimiter


def is_clockify_csv(path: Path) -> bool:
    """Check whether a CSV file looks like a Clockify detailed time report."""
    try:
        header, _ = _read_header(path)
    except (OSError, UnicodeDecodeError):
        return False
    return CLOCKIFY_SIGNATURE_COLUMNS.issubset(header)


class ClockifyConverter(BaseConverter):
    """
    Converter for Clockify detailed time report CSV exports.

    Used columns (others are ignored):
    - Project: Project name (empty -> "Imported Tasks")
    - Client: Added to the task notes
    - Description: Task title
    - Task: Clockify task, added to the task notes (and used as title if
      the description is empty)
    - Tags: Comma-separated tags
    - Start Date / Start Time / End Date / End Time: Time entry bounds
    - Duration (h) / Duration (decimal): Fallback for the tracked duration

    Clockify's date format depends on the user settings. ``date_order`` can be
    set to ``"DMY"``, ``"MDY"`` or ``"YMD"``; by default it is detected from
    the data.
    """

    def __init__(self, input_file: Path, date_order: str | None = None) -> None:
        super().__init__(input_file)
        self.date_order = date_order
        # (project, clockify task, description) -> Task
        self._task_index: dict[tuple[str, str, str], Task] = {}
        # project id -> day -> {"s": first start, "e": last end} (ms timestamps)
        self.work_times: dict[str, dict[str, dict[str, int]]] = {}

    def parse(self) -> None:
        """Parse the Clockify CSV and populate tasks, projects and tags."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Clockify CSV file not found: {self.input_file}")

        _, delimiter = _read_header(self.input_file)

        with open(self.input_file, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = [
                {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                for row in reader
            ]

        if self.date_order is None:
            self.date_order = self._detect_date_order(rows)

        for row_num, row in enumerate(rows, start=2):
            try:
                self._parse_entry(row)
            except Exception as e:
                print(f"Warning: Error parsing row {row_num}: {e}")

    # ------------------------------------------------------------------
    # Row handling
    # ------------------------------------------------------------------

    def _parse_entry(self, row: dict[str, str]) -> None:
        start = self._parse_datetime(
            row.get("Start Date", ""), row.get("Start Time", "")
        )
        if start is None:
            raise ValueError("missing or invalid start date/time")

        end = self._parse_datetime(row.get("End Date", ""), row.get("End Time", ""))
        if end is None or end < start:
            duration = self._parse_duration(row)
            if duration is None:
                raise ValueError("missing end time and duration")
            end = start + duration

        task = self._get_or_create_task(row, start)

        # Distribute the tracked time over the day(s) of the entry
        cursor = start
        while cursor < end:
            next_midnight = datetime.combine(
                cursor.date() + timedelta(days=1), datetime.min.time()
            )
            segment_end = min(end, next_midnight)
            day = cursor.strftime("%Y-%m-%d")
            ms = int((segment_end - cursor).total_seconds() * 1000)
            task.timeSpentOnDay[day] = task.timeSpentOnDay.get(day, 0) + ms
            task.timeSpent += ms
            self._record_work_time(task.projectId, day, cursor, segment_end)
            cursor = segment_end

        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        task.created = min(task.created, start_ms)
        task.modified = max(task.modified or 0, end_ms)

    def _get_or_create_task(self, row: dict[str, str], start: datetime) -> Task:
        project_name = row.get("Project", "") or DEFAULT_PROJECT_NAME
        clockify_task = row.get("Task", "")
        description = row.get("Description", "")

        key = (project_name, clockify_task, description)
        if key in self._task_index:
            task = self._task_index[key]
        else:
            notes = []
            if clockify_task and description:
                notes.append(f"Clockify task: {clockify_task}")
            if row.get("Client"):
                notes.append(f"Client: {row['Client']}")

            task = Task(
                id=generate_id(),
                title=description or clockify_task or NO_DESCRIPTION_TITLE,
                notes="\n".join(notes) or None,
                projectId=self._get_or_create_project(project_name).id,
                created=int(start.timestamp() * 1000),
            )
            self._task_index[key] = task
            self.tasks.append(task)

        for tag_name in (t.strip() for t in row.get("Tags", "").split(",")):
            tag = self._get_or_create_tag(tag_name)
            if tag and tag.id not in task.tagIds:
                task.tagIds.append(tag.id)

        return task

    def _record_work_time(
        self, project_id: str | None, day: str, start: datetime, end: datetime
    ) -> None:
        if not project_id:
            return
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        entry = self.work_times.setdefault(project_id, {}).setdefault(
            day, {"s": start_ms, "e": end_ms}
        )
        entry["s"] = min(entry["s"], start_ms)
        entry["e"] = max(entry["e"], end_ms)

    # ------------------------------------------------------------------
    # Date / time parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_date_order(rows: list[dict[str, str]]) -> str:
        """
        Detect whether dates are DD/MM/YYYY, MM/DD/YYYY or YYYY-MM-DD.

        Unambiguous values (a part > 12) decide. Otherwise, as a report usually
        spans few months but many days, the part with more distinct values is
        assumed to be the day. Ties fall back to DMY.
        """
        firsts: set[int] = set()
        seconds: set[int] = set()
        for row in rows:
            for col in ("Start Date", "End Date"):
                match = _DATE_RE.match(row.get(col, ""))
                if not match:
                    continue
                a, b, _ = match.groups()
                if len(a) == 4:
                    return "YMD"
                first, second = int(a), int(b)
                if first > 12:
                    return "DMY"
                if second > 12:
                    return "MDY"
                firsts.add(first)
                seconds.add(second)
        return "MDY" if len(seconds) > len(firsts) else "DMY"

    def _parse_date(self, date_str: str) -> str | None:
        """Parse a Clockify date into YYYY-MM-DD using the detected date order."""
        match = _DATE_RE.match(date_str or "")
        if not match:
            return None
        a, b, c = (int(x) for x in match.groups())
        order = self.date_order or "DMY"
        if order == "YMD" or len(match.group(1)) == 4:
            year, month, day = a, b, c
        elif order == "MDY":
            month, day, year = a, b, c
        else:
            day, month, year = a, b, c
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _parse_datetime(self, date_str: str, time_str: str) -> datetime | None:
        date = self._parse_date(date_str)
        if not date or not time_str:
            return None
        for fmt in _TIME_FORMATS:
            try:
                parsed = datetime.strptime(time_str.upper(), fmt)
            except ValueError:
                continue
            return datetime.strptime(date, "%Y-%m-%d").replace(
                hour=parsed.hour, minute=parsed.minute, second=parsed.second
            )
        return None

    @staticmethod
    def _parse_duration(row: dict[str, str]) -> timedelta | None:
        hms = row.get("Duration (h)", "")
        if hms:
            parts = hms.split(":")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                h, m, s = (int(p) for p in parts)
                return timedelta(hours=h, minutes=m, seconds=s)
        decimal = row.get("Duration (decimal)", "").replace(",", ".")
        if decimal:
            try:
                return timedelta(hours=float(decimal))
            except ValueError:
                pass
        return None

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def get_super_productivity_data(self) -> dict[str, Any]:
        """Generate Super Productivity data including per-project work times."""
        data = super().get_super_productivity_data()
        data["data"]["timeTracking"]["project"] = {
            project_id: {day: dict(times) for day, times in days.items()}
            for project_id, days in self.work_times.items()
        }
        return data
