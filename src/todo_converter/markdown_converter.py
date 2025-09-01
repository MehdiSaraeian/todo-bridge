"""
Markdown converter for todo lists.

This module handles conversion from Markdown format to Super Productivity JSON format.
Supports various markdown todo list formats including:
- GitHub-style task lists
- Simple bullet lists with [ ] and [x] checkboxes
- Nested lists for subtasks
- Headers (# ## ###) for project organization
- Notes-based subtask creation from indented content
- Preserves deep nesting (level 2+) as raw markdown in notes
- Inline tags using #hashtag format
- Due dates with and without time (@due:2023-12-31, @due:2023-12-31T14:00)
- Time estimates in parentheses (1h, 30m, 2h 30m)
- Attachments (@link:url "title", @file:path "title", @img:url "title")
- Bold text extraction to notes
- Mixed content handling (tasks and regular text in notes)
"""

import re
import time
from pathlib import Path
from typing import Any, Optional

from .base import BaseConverter
from .models import Attachment, Task, generate_id


class MarkdownConverter(BaseConverter):
    """
    Converter for Markdown format todo lists.

    Supports:
    - Task lists with [ ] for incomplete and [x] for complete
    - Nested lists for subtasks (first-level only become actual tasks)
    - Headers (# ## ###) for project organization
    - Inline tags using #hashtag format
    - Due dates in various formats (@due:2023-12-31, @2023-12-31)
    - Due dates with time (@due:2023-12-31T14:00)
    - Time estimates in parentheses (1h, 30m, 2h 30m)
    - Attachments (@link:url "title", @file:path "title", @img:url "title")
    - Notes extraction from indented content
    - Preserves deep nesting (level 2+) as raw markdown in notes
    - Bold text extraction to notes (**text**)
    - Mixed content handling in notes (tasks and regular text)
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

        # First pass: collect indented content as notes for tasks
        processed_lines = self._collect_indented_content_as_notes(lines)

        # Second pass: parse the processed content
        for line_num, line_data in enumerate(processed_lines, start=1):
            try:
                if line_data["type"] == "task":
                    self._parse_markdown_line_with_notes(
                        line_data["line"], line_data["notes"]
                    )
                else:
                    self._parse_markdown_line(line_data["line"])
            except Exception as e:
                print(f"Warning: Error parsing line {line_num}: {e}")
                continue

        # After parsing all tasks, process notes field for nested subtasks
        self._process_notes_for_subtasks()

        # Calculate parent task time estimates and time spent from children
        self._calculate_parent_task_times()

    def _create_task(
        self,
        content: str,
        checkbox: Optional[str] = None,
        notes: Optional[str] = None,
        parent_task: Optional[Task] = None,
        indent_level: int = 0,
    ) -> Task:
        """
        Unified task creation method that handles all task creation scenarios.

        Args:
            content: The task content string
            checkbox: The checkbox content (e.g., '[ ]', '[x]')
            notes: Optional notes content
            parent_task: Optional parent task for subtasks
            indent_level: Indentation level for hierarchy (ignored if parent_task is set)

        Returns:
            Created Task object
        """
        # Parse task content
        task_info = self._parse_task_content(content)

        # Determine completion status
        is_done = False
        if checkbox:
            checkbox_clean = checkbox.strip().lower()
            is_done = checkbox_clean in ["[x]", "[X]"]

        # Create task with conditional fields
        task = Task(
            id=generate_id(),
            title=task_info["title"],
            notes=self._merge_notes(task_info.get("notes"), notes),
            isDone=is_done,
            timeEstimate=task_info["time_estimate"],
            dueDay=task_info["due_date"],
            dueWithTime=task_info.get("due_with_time"),
            parentId=None,  # Will be set by _establish_parent_child_relationship if needed
        )

        # Handle explicit time spent from task content first
        self._handle_explicit_time_spent(task, task_info)

        # Handle completion
        if is_done:
            task.doneOn = task.created
            # Add timeSpentOnDay if task is completed and no explicit time was set
            if not task.timeSpentOnDay:
                self._add_time_spent_for_completed_task(task)

        # Handle attachments
        for attachment_data in task_info.get("attachments", []):
            attachment = Attachment(
                id=attachment_data["id"],
                type=attachment_data["type"],
                path=attachment_data["path"],
                title=attachment_data["title"],
            )
            task.attachments.append(attachment)

        # Handle project assignment (only for non-subtasks)
        if not parent_task:
            project_name = self.current_project_name or "Imported Tasks"
            project = self._get_or_create_project(project_name)
            task.projectId = project.id

        # Handle tags
        for tag_name in task_info["tags"]:
            tag = self._get_or_create_tag(tag_name)
            if tag:
                task.tagIds.append(tag.id)

        # Handle parent-child relationship if parent_task is provided (for notes-based subtasks)
        if parent_task:
            self._establish_parent_child_relationship(parent_task, task)

        # Handle hierarchy (only for non-subtasks and if using direct hierarchy)
        if not parent_task and indent_level > 0:
            self._handle_task_hierarchy(indent_level, task)

        return task

    def _collect_indented_content_as_notes(
        self, lines: list[str]
    ) -> list[dict[str, Any]]:
        """
        Collect indented content as notes for tasks instead of processing as subtasks.

        Args:
            lines: List of lines from the markdown file

        Returns:
            List of processed line data with notes attached to tasks
        """
        processed_lines: list[dict[str, Any]] = []
        current_task_line = None
        current_notes: list[str] = []

        for line in lines:
            stripped_line = line.rstrip()

            # Check if this is a header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", stripped_line)
            if header_match:
                # Finalize current task if any
                if current_task_line is not None:
                    processed_lines.append(
                        {
                            "type": "task",
                            "line": current_task_line,
                            "notes": "\n".join(current_notes).strip()
                            if current_notes
                            else "",
                        }
                    )
                    current_task_line = None
                    current_notes = []

                # Add header as regular line to be processed normally
                processed_lines.append(
                    {"type": "regular", "line": stripped_line, "notes": ""}
                )
                continue

            # Check if this is a task item
            task_match = re.match(
                r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])?\s*(.+)$", stripped_line
            )
            bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", stripped_line)

            if task_match or bare_task_match:
                indent = (
                    task_match.group(1)
                    if task_match is not None
                    else bare_task_match.group(1)
                    if bare_task_match is not None
                    else ""
                )

                # If this is a root level task (no or minimal indentation)
                if len(indent) == 0:
                    # Finalize previous task if any
                    if current_task_line is not None:
                        processed_lines.append(
                            {
                                "type": "task",
                                "line": current_task_line,
                                "notes": "\n".join(current_notes).strip()
                                if current_notes
                                else "",
                            }
                        )

                    # Start new task
                    current_task_line = stripped_line
                    current_notes = []
                else:
                    # This is indented content - add to notes
                    if current_task_line is not None:
                        current_notes.append(stripped_line)
                    else:
                        # No current task, treat as regular line
                        processed_lines.append(
                            {"type": "regular", "line": stripped_line, "notes": ""}
                        )
            else:
                # Non-task line
                if current_task_line is not None and stripped_line.strip():
                    # Add to current task's notes if it has content
                    current_notes.append(stripped_line)
                elif current_task_line is not None and not stripped_line.strip():
                    # Empty line - add to notes to preserve formatting
                    current_notes.append(stripped_line)
                else:
                    # No current task, treat as regular line
                    processed_lines.append(
                        {"type": "regular", "line": stripped_line, "notes": ""}
                    )

        # Handle the last task
        if current_task_line is not None:
            processed_lines.append(
                {
                    "type": "task",
                    "line": current_task_line,
                    "notes": "\n".join(current_notes).strip() if current_notes else "",
                }
            )

        return processed_lines

    def _parse_markdown_line_with_notes(self, line: str, notes: str) -> None:
        """
        Parse a markdown line that represents a task with associated notes.

        Args:
            line: The task line
            notes: The associated notes content
        """
        # Check for task items
        task_match = re.match(r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])?\s*(.+)$", line)
        if task_match:
            indent = task_match.group(1)
            checkbox = task_match.group(3)
            content = task_match.group(4)

            self._handle_task_item_with_notes(indent, checkbox, content, notes)
            return

        # Check for bare task lists (lines starting with [ ] or [x])
        bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", line)
        if bare_task_match:
            indent = bare_task_match.group(1)
            checkbox = bare_task_match.group(2)
            content = bare_task_match.group(3)

            self._handle_task_item_with_notes(indent, checkbox, content, notes)
            return

    def _handle_task_item_with_notes(
        self, indent: str, checkbox: Optional[str], content: str, notes: str
    ) -> None:
        """
        Handle a task item from markdown with associated notes.

        Args:
            indent: The indentation string
            checkbox: The checkbox content (e.g., '[ ]', '[x]')
            content: The task content
            notes: The associated notes content
        """
        # Parse task content
        self._parse_task_content(content)

        # Determine completion status
        if checkbox:
            checkbox.strip().lower()

        # Create task using unified method
        task = self._create_task(content, checkbox, notes)

        # Add to tasks list - hierarchy will be handled in notes processing
        self.tasks.append(task)

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

        # Create task using unified method
        task = self._create_task(content, checkbox, indent_level=indent_level)

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

        # Extract time spent patterns BEFORE due dates to avoid conflicts
        time_spent_data = self._parse_time_spent_patterns(content)
        if time_spent_data["time_spent"] > 0:
            result["time_spent"] = time_spent_data["time_spent"]
            if time_spent_data["time_spent_date"]:
                result["time_spent_date"] = time_spent_data["time_spent_date"]
            # Remove the time spent patterns from content
            content = time_spent_data["remaining_content"]

        # Extract due dates: @due:2023-12-31, @2023-12-31, due: 12/31/2023
        # Also support due dates with time: @due:2023-12-31T14:00
        due_patterns = [
            r"@due:(\S+)",
            r"@(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})?)",
            r"@(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
            r"due:\s*(\S+)",
            r"due\s*(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})?)",
            r"due\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
        ]

        for pattern in due_patterns:
            due_match = re.search(pattern, content, re.IGNORECASE)
            if due_match:
                due_str = due_match.group(1)
                if "T" in due_str or ":" in due_str:
                    # Date with time
                    due_with_time = self._parse_date_with_time(due_str)
                    if due_with_time:
                        result["due_with_time"] = due_with_time
                        result["due_date"] = (
                            due_str.split("T")[0]
                            if "T" in due_str
                            else due_str.split()[0]
                        )
                else:
                    # Date only
                    due_date = self._parse_date(due_str)
                    if due_date:
                        result["due_date"] = due_date
                # Remove due date from content
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)
                break

        # Extract attachments: @link:url, @file:path, @img:url
        attachment_patterns = [
            (r"@link:(\S+)(?:\s+\"([^\"]+)\")?", "LINK"),
            (r"@file:(\S+)(?:\s+\"([^\"]+)\")?", "FILE"),
            (r"@img:(\S+)(?:\s+\"([^\"]+)\")?", "IMG"),
        ]

        attachments = []
        for pattern, attachment_type in attachment_patterns:
            attachment_matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in attachment_matches:
                path = match.group(1)
                title = match.group(2) if match.group(2) else None

                attachment = {
                    "id": generate_id(),
                    "type": attachment_type,
                    "path": path,
                    "title": title,
                }
                attachments.append(attachment)

                # Remove attachment from content
                content = content.replace(match.group(0), "")

        result["attachments"] = attachments

        # Extract time spent: @spent:2h@2025-08-30, @logged:1h, @worked:30m
        time_spent_patterns = [
            r"@spent:([^@\s]+)@(\d{4}-\d{2}-\d{2})",  # @spent:2h@2025-08-30
            r"@logged:([^@\s]+)@(\d{4}-\d{2}-\d{2})",  # @logged:1h@2025-08-30
            r"@worked:([^@\s]+)@(\d{4}-\d{2}-\d{2})",  # @worked:30m@2025-08-30
            r"@spent:([^@\s]+)(?![^\s]*@\d{4}-\d{2}-\d{2})",  # @spent:2h (no date)
            r"@logged:([^@\s]+)(?![^\s]*@\d{4}-\d{2}-\d{2})",  # @logged:1h (no date)
            r"@worked:([^@\s]+)(?![^\s]*@\d{4}-\d{2}-\d{2})",  # @worked:30m (no date)
        ]

        for i, pattern in enumerate(time_spent_patterns):
            spent_match = re.search(pattern, content, re.IGNORECASE)
            if spent_match:
                time_str = spent_match.group(1)
                # First 3 patterns have date, last 3 don't
                date_str = (
                    spent_match.group(2)
                    if i < 3 and len(spent_match.groups()) > 1
                    else None
                )

                # Parse time spent
                spent_ms = self._parse_time_estimate(time_str)
                if spent_ms > 0:
                    result["time_spent"] = spent_ms
                    result["time_spent_date"] = (
                        date_str  # Will use current date if None
                    )

                # Remove time spent from content
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)
                break

        # Extract markdown bold formatting once and convert to notes
        bold_pattern = r"\*\*([^*]+)\*\*"
        bold_matches = re.findall(bold_pattern, content)
        if bold_matches:
            notes_parts = [f"**{bold_text}**" for bold_text in bold_matches]
            result["notes"] = "\n".join(notes_parts)
            # Remove bold formatting from title
            content = re.sub(bold_pattern, r"\1", content)

        # Clean up title
        result["title"] = self._clean_text(content)

        return result

    def _establish_parent_child_relationship(
        self, parent_task: Task, child_task: Task
    ) -> None:
        """
        Establish parent-child relationship between tasks with proper inheritance.

        Args:
            parent_task: The parent task
            child_task: The child task
        """
        child_task.parentId = parent_task.id
        parent_task.subTaskIds.append(child_task.id)

        # Inherit tags from parent (but NOT project - subtasks shouldn't appear in project view)
        if not child_task.tagIds:  # Only inherit if child doesn't have its own tags
            child_task.tagIds = parent_task.tagIds.copy()
        # Note: projectId is intentionally not inherited - subtasks should not appear as standalone project tasks

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
            self._establish_parent_child_relationship(parent_task, task)

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

    def _parse_date_with_time(self, date_str: str) -> Optional[int]:
        """
        Parse a date string with time into milliseconds timestamp.

        Args:
            date_str: Date string (e.g., "2023-12-31T14:00", "12/31/2023 2:00 PM")

        Returns:
            Timestamp in milliseconds or None if parsing fails
        """
        import datetime

        # Common date/time patterns
        patterns = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M",
            "%m-%d-%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        for pattern in patterns:
            try:
                dt = datetime.datetime.strptime(date_str, pattern)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue

        return None

    def _parse_time_spent_patterns(self, content: str) -> dict[str, Any]:
        """
        Parse time spent patterns like @worked:25m, @spent:1h, @logged:30m@2025-08-29

        Returns:
            dict with time_spent (in ms), time_spent_date, and remaining_content
        """
        result = {
            "time_spent": 0,
            "time_spent_date": None,
            "remaining_content": content,
        }

        # Patterns for time spent with optional date
        # @worked:25m@2025-08-29, @spent:1h, @logged:30m@date
        time_spent_patterns = [
            r"@(?:worked|spent|logged):(\d+(?:\.\d+)?)\s*([hm]|hour|hours|min|mins|minute|minutes)(?:@(\d{4}-\d{2}-\d{2}))?",
        ]

        for pattern in time_spent_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                time_value, time_unit, date_str = match

                # Convert time to milliseconds
                time_ms = self._parse_time_estimate(f"{time_value}{time_unit}")
                if time_ms > 0:
                    result["time_spent"] = time_ms

                    # Parse date if present
                    if date_str:
                        result["time_spent_date"] = date_str

                    # Remove the matched pattern from content
                    full_match = f"@(?:worked|spent|logged):{time_value}\\s*{time_unit}"
                    if date_str:
                        full_match += f"@{date_str}"
                    result["remaining_content"] = re.sub(
                        full_match, "", content, flags=re.IGNORECASE
                    )
                    break

        return result

    def _merge_notes(
        self, content_notes: Optional[str], indented_notes: Optional[str]
    ) -> Optional[str]:
        """
        Merge notes from task content (like bold text) with indented notes.

        Args:
            content_notes: Notes extracted from the task content (e.g., bold text)
            indented_notes: Notes from indented content below the task

        Returns:
            Merged notes or None if both are empty
        """
        parts = []

        if content_notes and content_notes.strip():
            parts.append(content_notes.strip())

        if indented_notes and indented_notes.strip():
            # Preserve indentation for indented_notes by only removing trailing whitespace
            parts.append(indented_notes.rstrip())

        if parts:
            return "\n\n".join(parts)

        return None

    def _process_notes_for_subtasks(self) -> None:
        """
        Process the notes field of all tasks to create subtasks from markdown lists.
        Only creates actual Task objects for first-level subtasks, preserving deeper
        nesting as raw markdown in the notes field of the immediate child tasks.
        """
        # Process tasks in order to ensure parent-child relationships are maintained
        for task in self.tasks[
            :
        ]:  # Create a copy to iterate over since we'll modify the list
            if task.notes:
                subtasks = self._parse_notes_for_subtasks(task.notes, task)
                if subtasks:
                    # Add subtasks to the main tasks list
                    self.tasks.extend(subtasks)
                    # Parent-child relationships are already established in _create_task
                    # Clear the notes that were converted to subtasks
                    task.notes = self._clean_processed_notes(task.notes)

    def _parse_notes_for_subtasks(self, notes: str, parent_task: Task) -> list[Task]:
        """
        Parse notes content and extract first-level markdown task lists as subtasks.

        Args:
            notes: The notes content to parse
            parent_task: The parent task object

        Returns:
            List of subtask objects created from first-level markdown lists
        """
        if not notes:
            return []

        lines = notes.split("\n")
        subtasks = []
        current_subtask_lines: list[str] = []
        in_first_level_task = False

        for line in lines:
            # Check if this is a first-level task list item (must have checkbox)
            task_match = re.match(r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])\s*(.+)$", line)
            bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", line)

            if task_match or bare_task_match:
                indent = (
                    task_match.group(1)
                    if task_match is not None
                    else bare_task_match.group(1)
                    if bare_task_match is not None
                    else ""
                )

                # If this is a root level task (no or minimal indentation)
                if len(indent) <= 2:  # Consider 0-2 spaces as first level
                    # If we were building a previous subtask, finalize it
                    if in_first_level_task and current_subtask_lines:
                        subtask = self._create_subtask_from_lines(
                            current_subtask_lines, parent_task
                        )
                        if subtask:
                            subtasks.append(subtask)

                    # Start new subtask
                    current_subtask_lines = [line]
                    in_first_level_task = True
                else:
                    # This is a nested item, add to current subtask if we're in one
                    if in_first_level_task:
                        current_subtask_lines.append(line)
            else:
                # Non-task line, add to current subtask if we're in one
                if in_first_level_task:
                    current_subtask_lines.append(line)

        # Handle the last subtask
        if in_first_level_task and current_subtask_lines:
            subtask = self._create_subtask_from_lines(
                current_subtask_lines, parent_task
            )
            if subtask:
                subtasks.append(subtask)

        return subtasks

    def _create_subtask_from_lines(
        self, lines: list[str], parent_task: Task
    ) -> Optional[Task]:
        """
        Create a subtask from a list of lines.

        Args:
            lines: List of lines that define the subtask
            parent_task: The parent task object

        Returns:
            Created subtask or None if creation failed
        """
        if not lines:
            return None

        first_line = lines[0]

        # Parse the first line to get the main task info (must have checkbox)
        task_match = re.match(r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])\s*(.+)$", first_line)
        bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", first_line)

        if task_match:
            checkbox = task_match.group(3)
            content = task_match.group(4)
        elif bare_task_match:
            checkbox = bare_task_match.group(2)
            content = bare_task_match.group(3)
        else:
            return None

        # Prepare nested content as notes if there are additional lines
        nested_notes = None
        if len(lines) > 1:
            nested_lines = []
            for line in lines[1:]:
                # Remove one level of indentation for nested content
                if line.startswith("  "):
                    nested_lines.append(line[2:])
                elif line.startswith(" "):
                    nested_lines.append(line[1:])
                else:
                    nested_lines.append(line)

            if nested_lines:
                nested_notes = "\n".join(nested_lines).rstrip()

        # Create subtask using unified method
        subtask = self._create_task(content, checkbox, nested_notes, parent_task)

        return subtask

    def _clean_processed_notes(self, notes: str) -> Optional[str]:
        """
        Clean the notes by removing first-level task items that were converted to subtasks,
        while preserving other content that should remain as notes.

        Args:
            notes: Original notes content

        Returns:
            Cleaned notes content or None if empty
        """
        if not notes:
            return None

        lines = notes.split("\n")
        cleaned_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a first-level task list item (must have checkbox)
            task_match = re.match(r"^(\s*)([-*+]|\d+\.)\s*(\[[ xX]\])\s*(.+)$", line)
            bare_task_match = re.match(r"^(\s*)(\[[ xX]\])\s*(.+)$", line)

            if task_match or bare_task_match:
                indent = (
                    task_match.group(1)
                    if task_match is not None
                    else bare_task_match.group(1)
                    if bare_task_match is not None
                    else ""
                )

                if len(indent) <= 2:  # First level task - remove this entire block
                    # Skip this task and all its nested content
                    i += 1
                    # Skip all following lines that belong to this task (more indented)
                    while i < len(lines):
                        next_line = lines[i]
                        if not next_line.strip():  # Empty line
                            # Check if this empty line separates tasks or is within a task
                            j = i + 1
                            # Look ahead to find the next non-empty line
                            while j < len(lines) and not lines[j].strip():
                                j += 1

                            if j >= len(lines):
                                # End of content, skip remaining empty lines
                                break

                            next_non_empty = lines[j]
                            # Check if the next non-empty line is still part of this task
                            if (
                                next_non_empty.startswith("    ")
                                or next_non_empty.startswith("\t")
                                or re.match(r"^\s{3,}", next_non_empty)
                            ):
                                # Still indented content of this task
                                i += 1
                                continue
                            else:
                                # This empty line marks end of task block
                                # Keep the empty line and stop removing
                                cleaned_lines.append(next_line)
                                i += 1
                                break
                        elif (
                            next_line.startswith("    ")  # 4+ spaces indented
                            or next_line.startswith("\t")  # Tab indented
                            or re.match(r"^\s{3,}", next_line)
                        ):  # 3+ spaces (subtask content)
                            # This line belongs to the task we're removing
                            i += 1
                            continue
                        else:
                            # This line is not indented enough, so it's not part of the task
                            break
                    continue
                else:
                    # Nested task (more than 2 spaces) - keep it
                    cleaned_lines.append(line)
            else:
                # Non-task line - keep it
                cleaned_lines.append(line)

            i += 1

        # Join and clean up
        cleaned_content = "\n".join(cleaned_lines)
        # Remove excessive empty lines but keep structure
        cleaned_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned_content)
        cleaned_content = cleaned_content.strip()

        return cleaned_content if cleaned_content else None

    def _add_time_spent_for_completed_task(self, task: Task) -> None:
        """
        Add timeSpentOnDay and timeSpent for completed tasks.

        Args:
            task: The completed task to add time tracking to
        """
        if not task.isDone or task.timeEstimate == 0:
            return

        # Get the completion date in YYYY-MM-DD format
        import datetime

        completion_timestamp = task.doneOn or task.created
        completion_date = datetime.datetime.fromtimestamp(
            completion_timestamp / 1000
        ).strftime("%Y-%m-%d")

        # Set timeSpent to timeEstimate for completed tasks
        task.timeSpent = task.timeEstimate

        # Set timeSpentOnDay for the completion date
        task.timeSpentOnDay = {completion_date: task.timeEstimate}

    def _handle_explicit_time_spent(
        self, task: Task, task_info: dict[str, Any]
    ) -> None:
        """
        Handle explicitly specified time spent from task content.

        Args:
            task: The task to update
            task_info: Parsed task information containing time spent data
        """
        if "time_spent" in task_info and task_info["time_spent"] > 0:
            time_spent = task_info["time_spent"]

            # Determine the date for time spent
            if "time_spent_date" in task_info and task_info["time_spent_date"]:
                spent_date = task_info["time_spent_date"]
            else:
                # Use current date if no date specified
                import datetime

                spent_date = datetime.datetime.now().strftime("%Y-%m-%d")

            # Set timeSpent and timeSpentOnDay (this overrides automatic calculation)
            task.timeSpent = time_spent
            task.timeSpentOnDay = {spent_date: time_spent}

    def _calculate_parent_task_times(self) -> None:
        """
        Calculate time estimates and time spent for parent tasks based on their children.
        Parent tasks should have timeEstimate = sum of children timeEstimate.
        Parent tasks should have timeSpent = sum of children timeSpent.
        Parent tasks should have timeSpentOnDay = merged children timeSpentOnDay.
        """
        # Find all parent tasks (tasks that have children)
        parent_tasks = [task for task in self.tasks if task.subTaskIds]

        for parent_task in parent_tasks:
            # Find all child tasks
            child_tasks = [
                task for task in self.tasks if task.id in parent_task.subTaskIds
            ]

            if not child_tasks:
                continue

            # Calculate total time estimate from children
            total_time_estimate = sum(child.timeEstimate for child in child_tasks)
            parent_task.timeEstimate = total_time_estimate

            # Calculate total time spent from children
            total_time_spent = sum(child.timeSpent for child in child_tasks)
            parent_task.timeSpent = total_time_spent

            # Merge timeSpentOnDay from all children
            merged_time_spent_on_day: dict[str, int] = {}
            for child in child_tasks:
                for date, time_spent in child.timeSpentOnDay.items():
                    if date in merged_time_spent_on_day:
                        merged_time_spent_on_day[date] += time_spent
                    else:
                        merged_time_spent_on_day[date] = time_spent

            parent_task.timeSpentOnDay = merged_time_spent_on_day

            # If all children are done, mark parent as done
            all_children_done = all(child.isDone for child in child_tasks)
            if all_children_done and not parent_task.isDone:
                parent_task.isDone = True
                # Use the latest completion date from children
                latest_done_on = max(
                    (child.doneOn for child in child_tasks if child.doneOn),
                    default=parent_task.created,
                )
                parent_task.doneOn = latest_done_on
