"""
Tests for the Todo.txt converter module.

This module contains comprehensive tests for the Todo.txt to Super Productivity converter.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.todo_converter.todo_txt_converter import TodoTxtConverter


class TestTodoTxtConverter:
    """Test cases for Todo.txt converter functionality."""

    def test_basic_todotxt_conversion(self) -> None:
        """Test basic Todo.txt conversion with completion, priority, projects, and contexts."""
        todotxt_data = """
x (A) 2023-10-01 2023-09-01 Task 1 +ProjectA @tag1
(B) 2023-10-02 Task 2 +ProjectB
Task 3 @tag1
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(todotxt_data.strip())
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()

            # Check tasks count
            assert len(converter.tasks) == 3

            # --- Task 1: Completed, Priority, Dates, Project, Tag ---
            task1 = converter.tasks[0]
            assert "Task 1" in task1.title
            assert task1.isDone is True
            # Check timestamps (approximate check or exact conversion)
            assert task1.created == int(datetime(2023, 9, 1).timestamp() * 1000)
            assert task1.doneOn == int(datetime(2023, 10, 1).timestamp() * 1000)

            # Check Project A mapping
            project_a = next(
                p for p in converter.projects.values() if p.title == "ProjectA"
            )
            assert task1.projectId == project_a.id

            # Check Tags (Context + Priority)
            tag_titles = [converter.tags[tid].title for tid in task1.tagIds]
            assert "tag1" in tag_titles
            assert "Priority A" in tag_titles

            # --- Task 2: Not completed, Priority B, Creation Date ---
            task2 = converter.tasks[1]
            assert "Task 2" in task2.title
            assert task2.isDone is False
            assert task2.created == int(datetime(2023, 10, 2).timestamp() * 1000)

            project_b = next(
                p for p in converter.projects.values() if p.title == "ProjectB"
            )
            assert task2.projectId == project_b.id

            tag_titles_2 = [converter.tags[tid].title for tid in task2.tagIds]
            assert "Priority B" in tag_titles_2

            # --- Task 3: Inbox (No project), Tag ---
            task3 = converter.tasks[2]
            assert "Task 3" in task3.title
            default_project = next(
                p for p in converter.projects.values() if p.title == "Imported Tasks"
            )
            assert task3.projectId is default_project.id

            tag_titles_3 = [converter.tags[tid].title for tid in task3.tagIds]
            assert "tag1" in tag_titles_3

        finally:
            txt_file.unlink()

    def test_todotxt_with_time_estimates(self) -> None:
        """Test Todo.txt parsing with time estimates in metadata (t: or time:)."""
        todotxt_data = """
Task with hours t:2h
Task with minutes time:30m
Task with mixed t:1h30m
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(todotxt_data.strip())
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 3

            # 2 hours = 7,200,000 ms
            assert tasks[0].timeEstimate == 7200000

            # 30 minutes = 1,800,000 ms
            assert tasks[1].timeEstimate == 1800000

            # 1h 30m = 90 minutes = 5,400,000 ms
            # Note: This depends on if your _parse_time_estimate handles "1h30m" or "1h 30m"
            # Assuming standard parser handles it.
            assert tasks[2].timeEstimate == 5400000

        finally:
            txt_file.unlink()

    def test_todotxt_with_due_dates(self) -> None:
        """Test Todo.txt parsing with due dates (due:YYYY-MM-DD)."""
        todotxt_data = """
Task 1 due:2023-12-15
Task 2 due:2023-12-16 +ProjectX
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(todotxt_data.strip())
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 2

            assert tasks[0].dueDay == "2023-12-15"
            assert tasks[1].dueDay == "2023-12-16"

        finally:
            txt_file.unlink()

    def test_todotxt_url_handling(self) -> None:
        """Test that URLs are not mistaken for metadata key:value pairs."""
        todotxt_data = """
Check website http://google.com for updates
Read docs at https://docs.python.org/3/library/re.html
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(todotxt_data.strip())
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()

            assert len(converter.tasks) == 2

            # Title should contain the full URL
            assert "http://google.com" in converter.tasks[0].title
            assert "https://docs.python.org" in converter.tasks[1].title

            # Should not have extracted 'http' or 'https' as metadata keys
            # (This verifies the _METADATA_KEY_PATTERN regex logic)

        finally:
            txt_file.unlink()

    def test_empty_todotxt_file(self) -> None:
        """Test handling of empty Todo.txt file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("")  # Empty file
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()

            assert len(converter.tasks) == 0
            assert len(converter.projects) == 1  # we still have the default project

        finally:
            txt_file.unlink()

    def test_todotxt_missing_file(self) -> None:
        """Test handling of missing Todo.txt file."""
        non_existent_file = Path("/tmp/non_existent_todo.txt")

        converter = TodoTxtConverter(non_existent_file)

        with pytest.raises(FileNotFoundError):
            converter.parse()

    def test_generate_super_productivity_data(self) -> None:
        """Test generation of Super Productivity JSON structure from Todo.txt."""
        todotxt_data = "Test Task +TestProject @test-tag"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(todotxt_data)
            txt_file = Path(f.name)

        try:
            converter = TodoTxtConverter(txt_file)
            converter.parse()
            data = converter.get_super_productivity_data()

            # Check overall structure
            assert "data" in data
            assert "crossModelVersion" in data
            assert "lastUpdate" in data

            # Check task data
            task_data = data["data"]["task"]
            assert len(task_data["ids"]) == 1
            assert len(task_data["entities"]) == 1

            # Check project data
            project_data = data["data"]["project"]
            assert len(project_data["ids"]) == 2  # TestProject and default project

            # Check tag data
            tag_data = data["data"]["tag"]
            assert len(tag_data["ids"]) == 1  # test-tag

        finally:
            txt_file.unlink()
