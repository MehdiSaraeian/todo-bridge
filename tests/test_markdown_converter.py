"""
Tests for the Markdown converter module.

This module contains comprehensive tests for the Markdown to Super Productivity converter.
"""

import tempfile
from pathlib import Path

from src.todo_converter.markdown_converter import MarkdownConverter


class TestMarkdownConverter:
    """Test cases for Markdown converter functionality."""

    def test_basic_markdown_conversion(self) -> None:
        """Test basic markdown task list conversion."""
        markdown_content = """# Project Alpha

- [ ] Task 1
- [x] Task 2 (completed)
- [ ] Task 3 #important

## Project Beta

- [ ] Another task
  - [ ] Subtask 1
  - [ ] Subtask 2
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Check tasks
            assert len(converter.tasks) == 6  # 4 main tasks + 2 subtasks

            # Check projects
            project_titles = [p.title for p in converter.projects.values()]
            assert "Project Alpha" in project_titles
            assert "Project Beta" in project_titles

            # Check task completion status
            completed_tasks = [task for task in converter.tasks if task.isDone]
            assert len(completed_tasks) == 1
            assert completed_tasks[0].title == "Task 2 (completed)"

            # Check tags
            tag_titles = [t.title for t in converter.tags.values()]
            assert "important" in tag_titles

        finally:
            md_file.unlink()

    def test_markdown_with_time_estimates(self) -> None:
        """Test markdown parsing with time estimates."""
        markdown_content = """# Tasks with Time Estimates

- [ ] Quick task (15m)
- [ ] Medium task (1h)
- [ ] Long task (2h 30m)
- [ ] Another task (45 minutes)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 4

            # 15 minutes = 900,000 ms
            assert tasks[0].timeEstimate == 900000

            # 1 hour = 3,600,000 ms
            assert tasks[1].timeEstimate == 3600000

            # 2h 30m = 9,000,000 ms
            assert tasks[2].timeEstimate == 9000000

            # 45 minutes = 2,700,000 ms
            assert tasks[3].timeEstimate == 2700000

        finally:
            md_file.unlink()

    def test_markdown_with_due_dates(self) -> None:
        """Test markdown parsing with due dates."""
        markdown_content = """# Tasks with Due Dates

- [ ] Task with @due:2023-12-31
- [ ] Task with @2023-11-15
- [ ] Task due: 12/25/2023
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 3

            # Check due dates are parsed
            assert tasks[0].dueDay == "2023-12-31"
            assert tasks[1].dueDay == "2023-11-15"
            assert tasks[2].dueDay == "2023-12-25"

        finally:
            md_file.unlink()

    def test_markdown_nested_tasks(self) -> None:
        """Test markdown parsing with nested task hierarchy."""
        markdown_content = """# Nested Tasks Project

- [ ] Main Task 1
  - [ ] Subtask 1.1
  - [ ] Subtask 1.2
    - [ ] Sub-subtask 1.2.1
- [ ] Main Task 2
  - [ ] Subtask 2.1
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 6

            # Find main tasks (no parent)
            main_tasks = [task for task in tasks if task.parentId is None]
            assert len(main_tasks) == 2

            # Check subtask relationships
            main_task_1 = next(
                task for task in main_tasks if task.title == "Main Task 1"
            )
            assert len(main_task_1.subTaskIds) == 2

            # Find subtasks
            subtasks_1 = [task for task in tasks if task.parentId == main_task_1.id]
            assert len(subtasks_1) == 2

            # Check sub-subtask
            subtask_1_2 = next(
                task for task in subtasks_1 if task.title == "Subtask 1.2"
            )
            assert len(subtask_1_2.subTaskIds) == 1

        finally:
            md_file.unlink()

    def test_markdown_with_hashtags(self) -> None:
        """Test markdown parsing with hashtag tags."""
        markdown_content = """# Tagged Tasks

- [ ] Task with #urgent tag
- [ ] Task with multiple #work #home tags
- [ ] Task with #project-alpha #important
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 3

            # Check tags were created
            tag_titles = [t.title for t in converter.tags.values()]
            expected_tags = ["urgent", "work", "home", "project-alpha", "important"]
            for tag in expected_tags:
                assert tag in tag_titles

            # Check task tag assignments
            task1 = tasks[0]
            assert len(task1.tagIds) == 1

            task2 = tasks[1]
            assert len(task2.tagIds) == 2

            task3 = tasks[2]
            assert len(task3.tagIds) == 2

        finally:
            md_file.unlink()

    def test_markdown_bare_checkboxes(self) -> None:
        """Test markdown parsing with bare checkbox lists."""
        markdown_content = """# Simple Checkbox List

[ ] Unchecked task
[x] Checked task
[X] Another checked task
[ ] Task with **bold** text
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 4

            # Check completion status
            assert not tasks[0].isDone
            assert tasks[1].isDone
            assert tasks[2].isDone
            assert not tasks[3].isDone

            # Check bold text handling
            task_with_bold = tasks[3]
            assert "bold" in task_with_bold.title
            assert task_with_bold.notes is not None
            assert "**bold**" in task_with_bold.notes

        finally:
            md_file.unlink()

    def test_markdown_date_header(self) -> None:
        """Test markdown parsing with date in header."""
        markdown_content = """# To-Do List: 7/30/2025

- [ ] Task 1
- [ ] Task 2
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Check that project name was derived from header with date
            project_titles = [p.title for p in converter.projects.values()]
            date_project = next(
                (title for title in project_titles if "Tasks for" in title), None
            )
            assert date_project is not None
            assert "7/30/2025" in date_project

        finally:
            md_file.unlink()

    def test_empty_markdown_file(self) -> None:
        """Test handling of empty markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")  # Empty file
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            assert len(converter.tasks) == 0
            # Should still have default project
            assert len(converter.projects) == 1

        finally:
            md_file.unlink()

    def test_markdown_missing_file(self) -> None:
        """Test handling of missing markdown file."""
        non_existent_file = Path("/tmp/non_existent_file.md")

        converter = MarkdownConverter(non_existent_file)

        try:
            converter.parse()
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass  # Expected

    def test_mixed_markdown_formats(self) -> None:
        """Test markdown parsing with mixed bullet and numbered lists."""
        markdown_content = """# Mixed Format Tasks

- [ ] Bullet task 1
* [x] Bullet task 2 (different bullet)
+ [ ] Bullet task 3 (plus bullet)
1. [ ] Numbered task 1
2. [x] Numbered task 2
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 5

            # Check completion status
            completed_tasks = [task for task in tasks if task.isDone]
            assert len(completed_tasks) == 2

        finally:
            md_file.unlink()
