"""
CSV converter for todo lists.

This module handles conversion from CSV format to Super Productivity JSON format.
"""

import csv
from typing import Optional

from .base import BaseConverter
from .models import Task, generate_id


class CSVConverter(BaseConverter):
    """
    Converter for CSV format todo lists.

    Expected CSV columns:
    - title: Task title (required)
    - notes: Task notes (optional)
    - project: Project name (optional)
    - tags: Comma-separated tags (optional)
    - isDone: Boolean completion status (optional, default: false)
    - timeEstimate: Time estimate in human-readable format (optional)
    - created: Creation date (optional)
    - modified: Modification date (optional)
    - dueDay: Due date (optional)
    - dueWithTime: Due date with time (optional)
    - remindAt: Reminder time (optional)
    - subtasks: Pipe-separated subtask titles (optional)
    """

    def parse(self) -> None:
        """Parse CSV file and populate tasks, projects, and tags."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.input_file}")

        with open(self.input_file, encoding="utf-8") as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except (csv.Error, ValueError):
                # Fall back to comma if detection fails
                delimiter = ','

            reader = csv.DictReader(csvfile, delimiter=delimiter, skipinitialspace=True)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    task = self._parse_csv_row(row)
                    if task:
                        self.tasks.append(task)
                except Exception as e:
                    print(f"Warning: Error parsing row {row_num}: {e}")
                    continue

    def _parse_csv_row(self, row: dict[str, str]) -> Optional[Task]:
        """
        Parse a single CSV row into a Task object.

        Args:
            row: Dictionary representing a CSV row

        Returns:
            Task object or None if the row is invalid
        """
        # Title is required
        title = row.get("title", "").strip()
        if not title:
            return None

        # Create task with basic information
        task = Task(
            id=generate_id(), title=title, notes=row.get("notes", "").strip() or None
        )

        # Parse completion status (doneOn will be set after created is parsed)
        is_done_str = row.get("isDone", "").strip().lower()
        if is_done_str in ("true", "1", "yes", "completed", "done"):
            task.isDone = True

        # Parse time estimate
        time_estimate_str = row.get("timeEstimate", "").strip()
        if time_estimate_str:
            task.timeEstimate = self._parse_time_estimate(time_estimate_str)

        # Parse dates
        created_str = row.get("created", "").strip()
        if created_str:
            parsed_date = self._parse_date(created_str)
            if parsed_date:
                from datetime import datetime

                task.created = int(
                    datetime.strptime(parsed_date, "%Y-%m-%d").timestamp() * 1000
                )

        modified_str = row.get("modified", "").strip()
        if modified_str:
            parsed_date = self._parse_date(modified_str)
            if parsed_date:
                from datetime import datetime

                task.modified = int(
                    datetime.strptime(parsed_date, "%Y-%m-%d").timestamp() * 1000
                )

        # Ensure doneOn uses the (possibly) parsed created timestamp
        if task.isDone and not task.doneOn:
            task.doneOn = task.created

        due_day_str = row.get("dueDay", "").strip()
        if due_day_str:
            parsed_date = self._parse_date(due_day_str)
            if parsed_date:
                task.dueDay = parsed_date

        due_with_time_str = row.get("dueWithTime", "").strip()
        if due_with_time_str:
            try:
                from datetime import datetime

                parsed_datetime = datetime.fromisoformat(
                    due_with_time_str.replace("Z", "+00:00")
                )
                task.dueWithTime = int(parsed_datetime.timestamp() * 1000)
            except ValueError:
                # Try parsing as date only
                parsed_date = self._parse_date(due_with_time_str)
                if parsed_date:
                    from datetime import datetime

                    task.dueWithTime = int(
                        datetime.strptime(parsed_date, "%Y-%m-%d").timestamp() * 1000
                    )

        # Handle project
        project_name = row.get("project", "").strip()
        if project_name:
            project = self._get_or_create_project(project_name)
            task.projectId = project.id
        else:
            # Assign to default project
            default_project = self._get_or_create_project("Imported Tasks")
            task.projectId = default_project.id

        # Handle tags
        tags_str = row.get("tags", "").strip()
        if tags_str:
            tag_names = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            for tag_name in tag_names:
                tag = self._get_or_create_tag(tag_name)
                if tag:
                    task.tagIds.append(tag.id)

        # Handle subtasks
        subtasks_str = row.get("subtasks", "").strip()
        if subtasks_str:
            subtask_titles = [
                title.strip() for title in subtasks_str.split("|") if title.strip()
            ]
            for subtask_title in subtask_titles:
                subtask = Task(
                    id=generate_id(),
                    title=subtask_title,
                    projectId=task.projectId,
                    parentId=task.id,
                    tagIds=task.tagIds.copy(),
                )
                task.subTaskIds.append(subtask.id)
                self.tasks.append(subtask)

        return task
