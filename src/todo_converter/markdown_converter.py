"""
Markdown converter for todo lists.

This module handles conversion from Markdown format to Super Productivity JSON format.
Supports various markdown todo list formats including:
- GitHub-style task lists
- Simple bullet lists with [ ] and [x] checkboxes
- Nested lists for subtasks
- Headers for project organization
"""

import re
import time
from pathlib import Path
from typing import Any, Optional

from .base import BaseConverter
from .models import Task, generate_id


class MarkdownConverter(BaseConverter):
    """
    Converter for Markdown format todo lists.

    Supports:
    - Task lists with [ ] for incomplete and [x] for complete
    - Nested lists for subtasks
    - Headers (# ## ###) for project organization
    - Inline tags using #hashtag format
    - Due dates in various formats
    - Time estimates in parentheses
    """

    def __init__(self, input_file: Path) -> None:
        """Initialize the markdown converter."""
        super().__init__(input_file)
        self.current_project_name: Optional[str] = None
        self.task_stack: list[
            tuple[int, Task]
        ] = []  # (indent_level, task) for hierarchy

    def parse(self) -> None:
        """Parse Markdown file and populate tasks, projects, and tags."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {self.input_file}")

        with open(self.input_file, encoding="utf-8") as file:
            lines = file.readlines()

        for line_num, line in enumerate(lines, start=1):
            try:
                self._parse_markdown_line(line.rstrip())
            except Exception as e:
                print(f"Warning: Error parsing line {line_num}: {e}")
                continue

    def _parse_markdown_line(self, line: str) -> None:
        """
        Parse a single markdown line.

        Args:
            line: A line from the markdown file
        """
        # Skip empty lines
        if not line.strip():
            return

        # Check for headers (projects)
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            self._handle_header(header_match.group(2).strip())
            return

        # Check for task items
        task_match = re.match(r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])?\s*(.+)$", line)
        if task_match:
            indent = task_match.group(1)
            checkbox = task_match.group(3)
            content = task_match.group(4)

            self._handle_task_item(indent, checkbox, content)
            return

        # Check for bare task lists (lines starting with [ ] or [x])
        bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", line)
        if bare_task_match:
            indent = bare_task_match.group(1)
            checkbox = bare_task_match.group(2)
            content = bare_task_match.group(3)

            self._handle_task_item(indent, checkbox, content)
            return

    def _handle_header(self, header_text: str) -> None:
        """
        Handle markdown headers as project names.

        Args:
            header_text: The header text
        """
        # Clean up header text and use as project name
        project_name = self._clean_text(header_text)

        # Extract date from header if present
        date_match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", project_name)
        if date_match:
            # If header contains date, use it as project name prefix
            project_name = f"Tasks for {date_match.group(1)}"

        self.current_project_name = project_name
        # Clear task stack when starting new project
        self.task_stack.clear()

    def _handle_task_item(
        self, indent: str, checkbox: Optional[str], content: str
    ) -> None:
        """
        Handle a task item from markdown.

        Args:
            indent: The indentation string
            checkbox: The checkbox content (e.g., '[ ]', '[x]')
            content: The task content
        """
        indent_level = len(indent)

        # Parse task content
        task_info = self._parse_task_content(content)

        # Determine completion status
        is_done = False
        if checkbox:
            checkbox_clean = checkbox.strip().lower()
            is_done = checkbox_clean in ["[x]", "[X]"]

        # Create task
        task = Task(
            id=generate_id(),
            title=task_info["title"],
            notes=task_info["notes"],
            isDone=is_done,
            timeEstimate=task_info["time_estimate"],
            dueDay=task_info["due_date"],
        )

        if is_done:
            task.doneOn = task.created

        # Handle project assignment
        project_name = self.current_project_name or "Imported Tasks"
        project = self._get_or_create_project(project_name)
        task.projectId = project.id

        # Handle tags
        for tag_name in task_info["tags"]:
            tag = self._get_or_create_tag(tag_name)
            if tag:
                task.tagIds.append(tag.id)

        # Handle hierarchy (subtasks)
        self._handle_task_hierarchy(indent_level, task)

        self.tasks.append(task)

    def _parse_task_content(self, content: str) -> dict[str, Any]:
        """
        Parse task content to extract title, tags, dates, estimates, etc.

        Args:
            content: The task content string

        Returns:
            Dictionary with parsed task information
        """
        # Initialize result
        # Initialize result with default values
        result: dict[str, Any] = {
            "title": "",
            "notes": "",
            "created": int(time.time() * 1000),
            "due_date": None,
            "time_estimate": 0,
            "tags": [],
            "project_id": None,
            "parent_id": None,
            "is_done": False,
            "sub_tasks": [],
        }

        # Extract time estimates in parentheses: (1h), (30m), (2h 30m)
        # Only match if contains time units
        time_pattern = (
            r"\(([^)]*(?:\d+\s*(?:h|m|hour|hours|min|mins|minute|minutes))[^)]*)\)"
        )
        time_matches = re.findall(time_pattern, content, re.IGNORECASE)
        if time_matches:
            for time_str in time_matches:
                result["time_estimate"] += self._parse_time_estimate(time_str)
            # Remove time estimates from content
            content = re.sub(time_pattern, "", content, flags=re.IGNORECASE)

        # Extract hashtags as tags
        tag_pattern = r"#([\w-]+)"
        tag_matches = re.findall(tag_pattern, content)
        result["tags"] = tag_matches
        # Remove hashtags from content
        content = re.sub(tag_pattern, "", content)

        # Extract due dates: @due:2023-12-31, @2023-12-31, due: 12/31/2023
        due_patterns = [
            r"@due:(\S+)",
            r"@(\d{4}-\d{2}-\d{2})",
            r"@(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"due:\s*(\S+)",
            r"due\s*(\d{4}-\d{2}-\d{2})",
            r"due\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ]

        for pattern in due_patterns:
            due_match = re.search(pattern, content, re.IGNORECASE)
            if due_match:
                due_date = self._parse_date(due_match.group(1))
                if due_date:
                    result["due_date"] = due_date
                    # Remove due date from content
                    content = re.sub(pattern, "", content, flags=re.IGNORECASE)
                    break

        # Extract markdown formatting and convert to notes
        bold_pattern = r"\*\*([^*]+)\*\*"
        bold_matches = re.findall(bold_pattern, content)
        if bold_matches:
            notes_parts = []
            for bold_text in bold_matches:
                notes_parts.append(f"**{bold_text}**")
            if notes_parts:
                result["notes"] = "\n".join(notes_parts)
            # Remove bold formatting from title
            content = re.sub(bold_pattern, r"\1", content)

        # Clean up title
        result["title"] = self._clean_text(content)

        return result

    def _handle_task_hierarchy(self, indent_level: int, task: Task) -> None:
        """
        Handle task hierarchy based on indentation levels.

        Args:
            indent_level: The indentation level of the current task
            task: The current task
        """
        # Remove tasks from stack that are at same or higher indent level
        while self.task_stack and self.task_stack[-1][0] >= indent_level:
            self.task_stack.pop()

        # If we have a parent task, make this a subtask
        if self.task_stack:
            parent_level, parent_task = self.task_stack[-1]
            task.parentId = parent_task.id
            parent_task.subTaskIds.append(task.id)

            # Inherit project and tags from parent
            task.projectId = parent_task.projectId
            if not task.tagIds:  # Only inherit if task doesn't have its own tags
                task.tagIds = parent_task.tagIds.copy()

        # Add current task to stack
        self.task_stack.append((indent_level, task))

    def _clean_text(self, text: str) -> str:
        """
        Clean text by removing extra whitespace and special characters.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove multiple spaces and trim
        text = re.sub(r"\s+", " ", text).strip()

        return text
