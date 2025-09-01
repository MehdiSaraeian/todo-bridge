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
            assert len(tasks) == 5  # 2 main tasks + 3 first-level subtasks

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

            # Check that sub-subtask is preserved as notes in Subtask 1.2
            subtask_1_2 = next(
                task for task in subtasks_1 if task.title == "Subtask 1.2"
            )
            assert subtask_1_2.notes is not None
            assert "Sub-subtask 1.2.1" in subtask_1_2.notes

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

    def test_notes_based_subtask_creation(self) -> None:
        """Test creating subtasks from markdown lists in notes field."""
        markdown_content = """# Project with Notes Subtasks

- [ ] Parent task with subtasks #parent
  This task has some additional context.

  - [ ] First subtask (2h) #child
  - [ ] Second subtask (1h 30m) #child
    - [ ] Nested subtask-level1
      - [ ] Nested subtask-level2
  - [ ] Third subtask (1h 30m) #child

  Some additional notes about the parent task.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 parent + 3 subtasks from notes = 4 total tasks
            assert len(converter.tasks) == 4

            # Find parent task
            parent_task = next(
                task for task in converter.tasks if "Parent task" in task.title
            )
            assert parent_task is not None
            assert len(parent_task.subTaskIds) == 3

            # Check that subtasks were created from notes
            subtasks = [
                task for task in converter.tasks if task.parentId == parent_task.id
            ]
            assert len(subtasks) == 3

            # Check first subtask
            first_subtask = next(
                task for task in subtasks if "First subtask" in task.title
            )
            assert first_subtask.timeEstimate == 7200000  # 2h = 7,200,000 ms
            assert "child" in [
                converter.tags[tag_id].title for tag_id in first_subtask.tagIds
            ]

            # Check second subtask (should have nested content in notes)
            second_subtask = next(
                task for task in subtasks if "Second subtask" in task.title
            )
            assert second_subtask.timeEstimate == 5400000  # 1h 30m = 5,400,000 ms
            assert second_subtask.notes is not None
            assert "Nested subtask-level1" in second_subtask.notes
            assert "Nested subtask-level2" in second_subtask.notes

            # Check third subtask
            third_subtask = next(
                task for task in subtasks if "Third subtask" in task.title
            )
            assert third_subtask.timeEstimate == 5400000  # 1h 30m = 5,400,000 ms

        finally:
            md_file.unlink()

    def test_notes_subtasks_only_first_level(self) -> None:
        """Test that only first-level subtasks are created from notes."""
        markdown_content = """# Deep Nesting Test

- [ ] Main task

  - [ ] Level 1 subtask
    - [ ] Level 2 item (should be in notes)
      - [ ] Level 3 item (should be in notes)
    - [ ] Another level 2 item
  - [ ] Another level 1 subtask
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 main + 2 level-1 subtasks = 3 total tasks
            assert len(converter.tasks) == 3

            # Find main task
            main_task = next(
                task for task in converter.tasks if "Main task" in task.title
            )
            assert len(main_task.subTaskIds) == 2

            # Find level 1 subtasks
            level1_subtasks = [
                task for task in converter.tasks if task.parentId == main_task.id
            ]
            assert len(level1_subtasks) == 2

            # Check that first level 1 subtask has nested content in notes
            first_level1 = next(
                task for task in level1_subtasks if "Level 1 subtask" in task.title
            )
            assert first_level1.notes is not None
            assert "Level 2 item (should be in notes)" in first_level1.notes
            assert "Level 3 item (should be in notes)" in first_level1.notes
            assert "Another level 2 item" in first_level1.notes

        finally:
            md_file.unlink()

    def test_notes_mixed_content(self) -> None:
        """Test notes with mixed content (tasks and regular text)."""
        markdown_content = """# Mixed Content Test

- [ ] Task with mixed notes

  This is some regular text in the notes.

  - [ ] First subtask from notes
  - [ ] Second subtask from notes

  More regular text after the subtasks.

  **Important note:** This should be preserved.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 main + 2 subtasks = 3 total tasks
            assert len(converter.tasks) == 3

            # Find main task
            main_task = next(
                task
                for task in converter.tasks
                if "Task with mixed notes" in task.title
            )
            assert len(main_task.subTaskIds) == 2

            # Check that non-task content is preserved in notes
            # The notes should still contain the regular text content
            # but the task items should be removed
            assert main_task.notes is not None
            assert "This is some regular text" in main_task.notes
            assert "More regular text after" in main_task.notes
            assert "Important note" in main_task.notes
            # Task items should be removed from notes
            assert "First subtask from notes" not in main_task.notes
            assert "Second subtask from notes" not in main_task.notes

        finally:
            md_file.unlink()

    def test_notes_completion_status(self) -> None:
        """Test that completion status is preserved in notes-based subtasks."""
        markdown_content = """# Completion Status Test

- [ ] Parent task

  - [x] Completed subtask
  - [ ] Incomplete subtask
  - [X] Another completed subtask
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 parent + 3 subtasks = 4 total tasks
            assert len(converter.tasks) == 4

            # Find parent task
            parent_task = next(
                task for task in converter.tasks if "Parent task" in task.title
            )

            # Find subtasks
            subtasks = [
                task for task in converter.tasks if task.parentId == parent_task.id
            ]
            assert len(subtasks) == 3

            # Check completion status
            completed_subtasks = [task for task in subtasks if task.isDone]
            incomplete_subtasks = [task for task in subtasks if not task.isDone]

            assert len(completed_subtasks) == 2
            assert len(incomplete_subtasks) == 1

            # Check that completed tasks have doneOn timestamp
            for task in completed_subtasks:
                assert task.doneOn is not None

        finally:
            md_file.unlink()

    def test_extended_metadata_parsing(self) -> None:
        """Test parsing of extended metadata including attachments, due dates with time, etc."""
        markdown_content = """# Extended Metadata Test

- [ ] Task with attachments @link:https://example.com "Example Link" @file:/path/to/file.pdf "Important Doc" @img:https://example.com/image.jpg
- [ ] Task with due time @due:2023-12-31T14:00 #urgent
- [ ] Simple task with date @due:2023-12-25
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 3 tasks
            assert len(converter.tasks) == 3

            # Test attachments
            task_with_attachments = converter.tasks[0]
            assert len(task_with_attachments.attachments) == 3

            # Check link attachment
            link_attachment = next(
                att for att in task_with_attachments.attachments if att.type == "LINK"
            )
            assert link_attachment.path == "https://example.com"
            assert link_attachment.title == "Example Link"

            # Check file attachment
            file_attachment = next(
                att for att in task_with_attachments.attachments if att.type == "FILE"
            )
            assert file_attachment.path == "/path/to/file.pdf"
            assert file_attachment.title == "Important Doc"

            # Check image attachment
            img_attachment = next(
                att for att in task_with_attachments.attachments if att.type == "IMG"
            )
            assert img_attachment.path == "https://example.com/image.jpg"
            assert img_attachment.title is None  # No title provided

            # Test due date with time
            task_with_due_time = converter.tasks[1]
            assert task_with_due_time.dueDay == "2023-12-31"
            assert task_with_due_time.dueWithTime is not None

            # Test simple due date
            task_with_simple_date = converter.tasks[2]
            assert task_with_simple_date.dueDay == "2023-12-25"
            assert task_with_simple_date.dueWithTime is None

        finally:
            md_file.unlink()

    def test_comprehensive_task_features(self) -> None:
        """Test a comprehensive example with many task features combined."""
        markdown_content = """# Comprehensive Task Test

- [ ] Complex parent task (3h) @due:2025-08-31T09:00 #work #urgent @link:https://docs.example.com "Project Docs"

  This task has comprehensive notes and metadata.

  **Important:** Check all requirements first.

  - [ ] Subtask 1 (1h) @due:2025-08-30 #work
    Notes for subtask 1.
    - [ ] Deep nested item
      - [ ] Very deep item
  - [x] Completed subtask (30m) #work
  - [ ] Final subtask (1h 30m) @file:/project/specs.pdf "Specifications" #work

  Additional parent notes after subtasks.

  Links and references should be preserved.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 parent + 3 subtasks = 4 total tasks
            assert len(converter.tasks) == 4

            # Find parent task
            parent_task = next(
                task for task in converter.tasks if "Complex parent task" in task.title
            )

            # Test parent task properties
            assert parent_task.timeEstimate == 10800000  # 3h in milliseconds
            assert parent_task.dueDay == "2025-08-31"
            assert parent_task.dueWithTime is not None
            assert len(parent_task.tagIds) >= 2  # work and urgent tags
            assert len(parent_task.attachments) == 1
            assert parent_task.attachments[0].type == "LINK"
            assert parent_task.attachments[0].path == "https://docs.example.com"
            assert parent_task.attachments[0].title == "Project Docs"

            # Test parent notes preservation
            assert parent_task.notes is not None
            assert "This task has comprehensive notes" in parent_task.notes
            assert "Important:** Check all requirements" in parent_task.notes
            assert "Additional parent notes after subtasks" in parent_task.notes
            assert "Links and references should be preserved" in parent_task.notes

            # Test subtasks
            subtasks = [
                task for task in converter.tasks if task.parentId == parent_task.id
            ]
            assert len(subtasks) == 3

            # Test completed subtask
            completed_subtask = next(
                task for task in subtasks if "Completed subtask" in task.title
            )
            assert completed_subtask.isDone is True
            assert completed_subtask.doneOn is not None
            assert completed_subtask.timeEstimate == 1800000  # 30m in milliseconds

            # Test subtask with attachment
            subtask_with_file = next(
                task for task in subtasks if "Final subtask" in task.title
            )
            assert len(subtask_with_file.attachments) == 1
            assert subtask_with_file.attachments[0].type == "FILE"
            assert subtask_with_file.attachments[0].path == "/project/specs.pdf"
            assert subtask_with_file.attachments[0].title == "Specifications"

            # Test subtask with nested content
            subtask_with_nested = next(
                task for task in subtasks if "Subtask 1" in task.title
            )
            assert subtask_with_nested.notes is not None
            assert "Notes for subtask 1" in subtask_with_nested.notes
            assert "Deep nested item" in subtask_with_nested.notes
            assert "Very deep item" in subtask_with_nested.notes

        finally:
            md_file.unlink()

    def test_parent_and_child_notes_preservation(self) -> None:
        """Test that both parent and child tasks can have their own notes."""
        markdown_content = """# Parent and Child Notes Test

- [ ] Parent task with notes #parent

  This is important context for the parent task.

  **Remember:** Check the documentation first.

  - [ ] Child task 1 (1h) #child
    This child has its own notes.
    - [ ] Nested item for child 1
  - [ ] Child task 2 (2h) #child
    This child also has notes.
    And multiple lines of notes.

  More parent notes after the children.

  Final parent note.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 parent + 2 children = 3 total tasks
            assert len(converter.tasks) == 3

            # Find parent task
            parent_task = next(
                task for task in converter.tasks if "Parent task" in task.title
            )
            assert parent_task is not None
            assert len(parent_task.subTaskIds) == 2

            # Check parent task notes
            assert parent_task.notes is not None
            assert "This is important context for the parent task" in parent_task.notes
            assert "Remember:** Check the documentation first" in parent_task.notes
            assert "More parent notes after the children" in parent_task.notes
            assert "Final parent note" in parent_task.notes

            # The child task items should be removed from parent notes
            assert "Child task 1" not in parent_task.notes
            assert "Child task 2" not in parent_task.notes

            # Find child tasks
            child_tasks = [
                task for task in converter.tasks if task.parentId == parent_task.id
            ]
            assert len(child_tasks) == 2

            # Check first child task
            child1 = next(task for task in child_tasks if "Child task 1" in task.title)
            assert child1.notes is not None
            assert "This child has its own notes" in child1.notes
            assert "Nested item for child 1" in child1.notes
            assert child1.timeEstimate == 3600000  # 1h

            # Check second child task
            child2 = next(task for task in child_tasks if "Child task 2" in task.title)
            assert child2.notes is not None
            assert "This child also has notes" in child2.notes
            assert "And multiple lines of notes" in child2.notes
            assert child2.timeEstimate == 7200000  # 2h

        finally:
            md_file.unlink()

    def test_mixed_notes_and_tasks_complex(self) -> None:
        """Test complex scenarios with mixed notes and tasks at different levels."""
        markdown_content = """# Complex Mixed Content

- [ ] Main task

  Initial notes for main task.

  - [ ] Subtask A
    Notes for subtask A.
    - [ ] Deep item A1
    - [ ] Deep item A2
      - [ ] Very deep item
    More notes for subtask A.

  Middle notes for main task.

  - [ ] Subtask B
    Different notes for subtask B.

  Final notes for main task.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            md_file = Path(f.name)

        try:
            converter = MarkdownConverter(md_file)
            converter.parse()

            # Should have 1 main + 2 subtasks = 3 total tasks
            assert len(converter.tasks) == 3

            # Find main task
            main_task = next(
                task for task in converter.tasks if "Main task" in task.title
            )
            assert main_task.notes is not None
            assert "Initial notes for main task" in main_task.notes
            assert "Middle notes for main task" in main_task.notes
            assert "Final notes for main task" in main_task.notes
            # Subtask lines should be removed
            assert "Subtask A" not in main_task.notes
            assert "Subtask B" not in main_task.notes

            # Find subtasks
            subtasks = [
                task for task in converter.tasks if task.parentId == main_task.id
            ]
            assert len(subtasks) == 2

            # Check subtask A
            subtask_a = next(task for task in subtasks if "Subtask A" in task.title)
            assert subtask_a.notes is not None
            assert "Notes for subtask A" in subtask_a.notes
            assert "Deep item A1" in subtask_a.notes
            assert "Deep item A2" in subtask_a.notes
            assert "Very deep item" in subtask_a.notes
            assert "More notes for subtask A" in subtask_a.notes

            # Check subtask B
            subtask_b = next(task for task in subtasks if "Subtask B" in task.title)
            assert subtask_b.notes is not None
            assert "Different notes for subtask B" in subtask_b.notes

        finally:
            md_file.unlink()
