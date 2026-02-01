"""
Todo.txt converter for todo lists.

This module handles conversion from Todo.txt format to Super Productivity JSON format.
"""

import re
from datetime import datetime
from typing import Optional

from .base import BaseConverter
from .models import Task, generate_id


class TodoTxtConverter(BaseConverter):
    """
    Converter for Todo.txt format todo lists.
    
    Standard Todo.txt format:
    x (A) 2023-10-01 2023-09-01 Task description +Project @Context due:2023-10-15
    """

    # Regex patterns for parsing specific tokens within the description
    _PROJECT_PATTERN = re.compile(r"\+([\w-]+)")
    _CONTEXT_PATTERN = re.compile(r"@([\w-]+)")
    _KEY_VALUE_PATTERN = re.compile(r"(\w+):([\w\-\:]+)")
    _PRIORITY_PATTERN = re.compile(r"^\(([A-Z])\)$")
    _DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def parse(self) -> None:
        """Parse Todo.txt file and populate tasks, projects, and tags."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Todo.txt file not found: {self.input_file}")

        with open(self.input_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                
                try:
                    task = self._parse_todotxt_line(line)
                    if task:
                        self.tasks.append(task)
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    continue

    def _parse_todotxt_line(self, line: str) -> Optional[Task]:
        """
        Parse a single Todo.txt line into a Task object.

        Args:
            line: A string representing a single line in todo.txt

        Returns:
            Task object or None if the line is empty
        """
        tokens = line.strip().split()
        if not tokens:
            return None

        # Initialize parsing variables
        completed = False
        priority = None
        completion_date_str = None
        creation_date_str = None
        
        # 1. Check Completion (Must be at the very start)
        if tokens[0] == 'x':
            completed = True
            tokens.pop(0)

        # 2. Check Priority (Must be at start or after 'x')
        if tokens and self._PRIORITY_PATTERN.match(tokens[0]):
            priority = tokens[0][1]  # Extract 'A' from '(A)'
            tokens.pop(0)

        # 3. Check Dates
        # Logic: 
        # - If completed: 1st date = completion, 2nd date = creation.
        # - If not completed: 1st date = creation.
        date1 = None
        date2 = None
        
        if tokens and self._DATE_PATTERN.match(tokens[0]):
            date1 = tokens.pop(0)
            if tokens and self._DATE_PATTERN.match(tokens[0]):
                date2 = tokens.pop(0)

        if completed:
            completion_date_str = date1
            creation_date_str = date2
        else:
            creation_date_str = date1
            # If a second date was found but task is not completed, 
            # strictly speaking in todo.txt, it's part of the description.
            if date2:
                tokens.insert(0, date2)

        # Reconstruct description from remaining tokens to scan for tags/projects
        raw_description = " ".join(tokens)
        
        # Extract Projects, Contexts, and Metadata
        projects = self._PROJECT_PATTERN.findall(raw_description)
        contexts = self._CONTEXT_PATTERN.findall(raw_description)
        
        # Extract key:value pairs
        metadata = {}
        for match in self._KEY_VALUE_PATTERN.finditer(raw_description):
            key, value = match.groups()
            metadata[key.lower()] = value

        # Clean description: Remove +Project, @Context, and key:value to get clean title
        # Note: Some users prefer keeping them in the title. 
        # Here we strip them to match the CSV behavior of separating title from metadata.
        clean_title = raw_description
        clean_title = self._PROJECT_PATTERN.sub("", clean_title)
        clean_title = self._CONTEXT_PATTERN.sub("", clean_title)
        clean_title = self._KEY_VALUE_PATTERN.sub("", clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()

        if not clean_title:
            # Fallback if everything was metadata
            clean_title = "Untitled Task"

        # --- Build the Task Object ---
        
        task = Task(
            id=generate_id(),
            title=clean_title,
        )

        task.isDone = completed

        # Handle Dates (Convert to milliseconds timestamp)
        if creation_date_str:
            dt = datetime.strptime(creation_date_str, "%Y-%m-%d")
            task.created = int(dt.timestamp() * 1000)

        if completed and completion_date_str:
            dt = datetime.strptime(completion_date_str, "%Y-%m-%d")
            task.doneOn = int(dt.timestamp() * 1000)
        elif completed and task.created:
            # Fallback if no specific completion date is logged
            task.doneOn = task.created

        # Handle Metadata: Due Date
        if "due" in metadata:
            parsed_date = self._parse_date(metadata["due"])
            if parsed_date:
                task.dueDay = parsed_date

        # Handle Metadata: Time Estimate (e.g., t:30m)
        if "t" in metadata:
            task.timeEstimate = self._parse_time_estimate(metadata["t"])
        elif "time" in metadata:
            task.timeEstimate = self._parse_time_estimate(metadata["time"])

        # Handle Project
        # Todo.txt allows multiple projects. We take the first one as the main Project,
        # others could theoretically be tags, but we'll stick to one project for now.
        if projects:
            main_project = projects[0]
            project = self._get_or_create_project(main_project)
            task.projectId = project.id
        else:
            default_project = self._get_or_create_project("Imported Tasks")
            task.projectId = default_project.id

        # Handle Tags (Contexts)
        for context in contexts:
            tag = self._get_or_create_tag(context)
            if tag:
                task.tagIds.append(tag.id)
        
        # Add Priority as a tag if it exists (Super Productivity doesn't have A-Z priority field)
        if priority:
            priority_tag = self._get_or_create_tag(f"Priority {priority}")
            if priority_tag:
                task.tagIds.append(priority_tag.id)

        return task
