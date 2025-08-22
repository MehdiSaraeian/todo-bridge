"""
Main converter module for todo lists to Super Productivity format.

This module provides the main interface for converting todo lists from various
formats (CSV, Markdown) to Super Productivity JSON format.
"""

import json
from pathlib import Path
from typing import Any, Optional, Union

from .base import BaseConverter
from .csv_converter import CSVConverter
from .markdown_converter import MarkdownConverter


class TodoConverter:
    """
    Main converter class that handles multiple input formats.

    Supports:
    - CSV files (.csv)
    - Markdown files (.md, .markdown)
    """

    SUPPORTED_FORMATS: dict[str, type[BaseConverter]] = {
        ".csv": CSVConverter,
        ".md": MarkdownConverter,
        ".markdown": MarkdownConverter,
    }

    def __init__(self, input_file: Union[str, Path]) -> None:
        """
        Initialize the converter with an input file.

        Args:
            input_file: Path to the input file to convert

        Raises:
            ValueError: If the file format is not supported
            FileNotFoundError: If the input file doesn't exist
        """
        self.input_file = Path(input_file)

        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        file_extension = self.input_file.suffix.lower()
        if file_extension not in self.SUPPORTED_FORMATS:
            supported = ", ".join(self.SUPPORTED_FORMATS.keys())
            raise ValueError(
                f"Unsupported file format: {file_extension}. "
                f"Supported formats: {supported}"
            )

        # Initialize the appropriate converter
        converter_class = self.SUPPORTED_FORMATS[file_extension]
        self.converter: BaseConverter = converter_class(self.input_file)

    def convert(self) -> dict[str, Any]:
        """
        Convert the input file to Super Productivity JSON format.

        Returns:
            Dictionary containing the Super Productivity data structure
        """
        self.converter.parse()
        return self.converter.get_super_productivity_data()

    def convert_to_file(self, output_file: Union[str, Path], indent: int = 2) -> None:
        """
        Convert the input file and save as JSON file.

        Args:
            output_file: Path to the output JSON file
            indent: JSON indentation level for pretty printing
        """
        output_path = Path(output_file)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert and save
        data = self.convert()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        print(f"Successfully converted {self.input_file} to {output_path}")
        self._print_conversion_summary()

    def _print_conversion_summary(self) -> None:
        """Print a summary of the conversion results."""
        print("\nConversion Summary:")
        print(f"  Tasks: {len(self.converter.tasks)}")
        print(f"  Projects: {len(self.converter.projects)}")
        print(f"  Tags: {len(self.converter.tags)}")

        # Count completed vs incomplete tasks
        completed = sum(1 for task in self.converter.tasks if task.isDone)
        incomplete = len(self.converter.tasks) - completed
        print(f"  Completed tasks: {completed}")
        print(f"  Incomplete tasks: {incomplete}")

        # List projects
        if self.converter.projects:
            print("\nProjects created:")
            for project in self.converter.projects.values():
                task_count = len(project.taskIds)
                print(f"  - {project.title} ({task_count} tasks)")

        # List tags
        if self.converter.tags:
            print("\nTags created:")
            for tag in self.converter.tags.values():
                task_count = len(tag.taskIds)
                print(f"  - {tag.title} ({task_count} tasks)")


def convert_todo_list(
    input_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    indent: int = 2,
) -> Union[dict[str, Any], None]:
    """
    Convenience function to convert a todo list file.

    Args:
        input_file: Path to the input file to convert
        output_file: Path to the output JSON file (optional)
        indent: JSON indentation level for pretty printing

    Returns:
        Dictionary containing the Super Productivity data if no output_file,
        None if output_file is specified
    """
    converter = TodoConverter(input_file)

    if output_file:
        converter.convert_to_file(output_file, indent)
        return None
    else:
        return converter.convert()
