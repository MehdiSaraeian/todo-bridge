"""
Tests for the CSV converter module.

This module contains comprehensive tests for the CSV to Super Productivity converter.
"""

import csv
import tempfile
from pathlib import Path

import pytest

from src.todo_converter.csv_converter import CSVConverter


class TestCSVConverter:
    """Test cases for CSV converter functionality."""

    def test_basic_csv_conversion(self) -> None:
        """Test basic CSV conversion with minimal required fields."""
        csv_data = [
            ["title", "notes", "project", "tags", "isDone"],
            ["Task 1", "First task notes", "Project A", "tag1,tag2", "false"],
            ["Task 2", "", "Project B", "", "true"],
            ["Task 3", "Third task", "", "tag1", "false"],
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            # Check tasks
            assert len(converter.tasks) == 3

            task1 = converter.tasks[0]
            assert task1.title == "Task 1"
            assert task1.notes == "First task notes"
            assert not task1.isDone
            assert len(task1.tagIds) == 2

            task2 = converter.tasks[1]
            assert task2.title == "Task 2"
            assert task2.isDone
            assert task2.doneOn is not None

            task3 = converter.tasks[2]
            assert task3.title == "Task 3"
            assert len(task3.tagIds) == 1

            # Check projects
            assert len(converter.projects) == 3  # Project A, Project B, Imported Tasks
            project_titles = [p.title for p in converter.projects.values()]
            assert "Project A" in project_titles
            assert "Project B" in project_titles

            # Check tags
            assert len(converter.tags) == 2  # tag1, tag2
            tag_titles = [t.title for t in converter.tags.values()]
            assert "tag1" in tag_titles
            assert "tag2" in tag_titles

        finally:
            csv_file.unlink()

    def test_csv_with_time_estimates(self) -> None:
        """Test CSV parsing with time estimates."""
        csv_data = [
            ["title", "timeEstimate"],
            ["Task with hours", "2h"],
            ["Task with minutes", "30m"],
            ["Task with mixed", "1h 30m"],
            ["Task with number", "45"],  # Should be treated as minutes
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 4

            # 2 hours = 2 * 60 * 60 * 1000 = 7,200,000 ms
            assert tasks[0].timeEstimate == 7200000

            # 30 minutes = 30 * 60 * 1000 = 1,800,000 ms
            assert tasks[1].timeEstimate == 1800000

            # 1h 30m = 90 minutes = 5,400,000 ms
            assert tasks[2].timeEstimate == 5400000

            # 45 minutes = 2,700,000 ms
            assert tasks[3].timeEstimate == 2700000

        finally:
            csv_file.unlink()

    def test_csv_with_dates(self) -> None:
        """Test CSV parsing with various date formats."""
        csv_data = [
            ["title", "created", "dueDay"],
            ["Task 1", "2023-12-01", "2023-12-15"],
            ["Task 2", "12/01/2023", "12/15/2023"],
            ["Task 3", "01/12/2023", "15/12/2023"],  # DD/MM/YYYY format
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            tasks = converter.tasks
            assert len(tasks) == 3

            # Check due dates are parsed correctly
            assert tasks[0].dueDay == "2023-12-15"
            assert tasks[1].dueDay == "2023-12-15"

        finally:
            csv_file.unlink()

    def test_csv_with_subtasks(self) -> None:
        """Test CSV parsing with subtasks."""
        csv_data = [
            ["title", "subtasks"],
            ["Main Task", "Subtask 1|Subtask 2|Subtask 3"],
            ["Another Task", "Single Subtask"],
            ["No Subtasks", ""],
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            # Should have 3 main tasks + 4 subtasks = 7 total tasks
            assert len(converter.tasks) == 7

            # Find the main task with multiple subtasks
            main_task = next(
                task for task in converter.tasks if task.title == "Main Task"
            )
            assert len(main_task.subTaskIds) == 3

            # Check that subtasks exist and have correct parent
            subtask_ids = main_task.subTaskIds
            subtasks = [task for task in converter.tasks if task.id in subtask_ids]
            assert len(subtasks) == 3

            for subtask in subtasks:
                assert subtask.parentId == main_task.id
                assert subtask.projectId == main_task.projectId

        finally:
            csv_file.unlink()

    def test_empty_csv_file(self) -> None:
        """Test handling of empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("title\n")  # Just header
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            assert len(converter.tasks) == 0
            # Should still have default project
            assert len(converter.projects) == 1

        finally:
            csv_file.unlink()

    def test_csv_missing_file(self) -> None:
        """Test handling of missing CSV file."""
        non_existent_file = Path("/tmp/non_existent_file.csv")

        converter = CSVConverter(non_existent_file)

        with pytest.raises(FileNotFoundError):
            converter.parse()

    def test_csv_malformed_row(self) -> None:
        """Test handling of malformed CSV rows."""
        csv_data = [
            ["title", "notes"],
            ["Valid Task", "Valid notes"],
            ["", ""],  # Empty title - should be skipped
            ["Another Valid Task", "More notes"],
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()

            # Should have 2 tasks (empty title row skipped)
            assert len(converter.tasks) == 2
            assert converter.tasks[0].title == "Valid Task"
            assert converter.tasks[1].title == "Another Valid Task"

        finally:
            csv_file.unlink()

    def test_generate_super_productivity_data(self) -> None:
        """Test generation of Super Productivity JSON structure."""
        csv_data = [
            ["title", "project", "tags", "isDone"],
            ["Test Task", "Test Project", "test-tag", "false"],
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file = Path(f.name)

        try:
            converter = CSVConverter(csv_file)
            converter.parse()
            data = converter.get_super_productivity_data()

            # Check overall structure
            assert "data" in data
            assert "crossModelVersion" in data
            assert "lastUpdate" in data
            assert "timestamp" in data

            # Check task data
            task_data = data["data"]["task"]
            assert "ids" in task_data
            assert "entities" in task_data
            assert len(task_data["ids"]) == 1
            assert len(task_data["entities"]) == 1

            # Check project data
            project_data = data["data"]["project"]
            assert "ids" in project_data
            assert "entities" in project_data
            assert len(project_data["ids"]) == 2  # Test Project + Imported Tasks

            # Check tag data
            tag_data = data["data"]["tag"]
            assert "ids" in tag_data
            assert "entities" in tag_data
            assert len(tag_data["ids"]) == 1

        finally:
            csv_file.unlink()
