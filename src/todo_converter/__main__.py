"""
Main converter entry point.

This module provides the command-line interface for the todo list converter.
"""

import argparse
import json
import sys
from pathlib import Path

from .converter import TodoConverter, convert_todo_list

__all__ = ["TodoConverter", "convert_todo_list"]
__version__ = "1.0.0"


def main() -> None:
    """Main entry point for the converter CLI."""
    parser = argparse.ArgumentParser(
        description="Convert todo lists to Super Productivity JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new Super Productivity JSON from CSV/Markdown:
  python -m src.todo_converter todos.csv todos_super_productivity.json
  python -m src.todo_converter todos.md
  python -m src.todo_converter my_tasks.csv --indent 4

  # Merge new tasks into existing Super Productivity backup:
  python -m src.todo_converter new_tasks.csv --merge backup.json merged_backup.json
  python -m src.todo_converter daily_todos.md --merge super-productivity-backup.json updated_backup.json

Supported input formats:
  - CSV files (.csv)
  - Markdown files (.md, .markdown)

CSV Format:
  Expected columns: title, notes, project, tags, isDone, timeEstimate,
  created, modified, dueDay, dueWithTime, remindAt, subtasks

Markdown Format:
  - Task lists with [ ] for incomplete and [x] for complete
  - Headers for project organization
  - Nested lists for subtasks
  - Inline tags using #hashtag format
  - Time estimates in parentheses: (1h), (30m)
  - Due dates: @due:2023-12-31, @2023-12-31

Merge Mode:
  When using --merge, new tasks are added to existing projects by name.
  If a project doesn't exist, it will be created. Tasks are never overwritten.
        """,
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input todo list file (CSV or Markdown)",
    )

    parser.add_argument(
        "output_file",
        type=str,
        nargs="?",
        help="Path to the output JSON file (required when using --merge, optional otherwise)",
    )

    parser.add_argument(
        "--merge",
        type=str,
        metavar="BACKUP_FILE",
        help="Merge with existing Super Productivity backup file instead of creating new",
    )

    parser.add_argument(
        "--indent", type=int, default=2, help="JSON indentation level (default: 2)"
    )

    parser.add_argument(
        "--version", action="version", version="Super Productivity Todo Converter 1.0.0"
    )

    args = parser.parse_args()

    try:
        # Initialize converter
        converter = TodoConverter(args.input_file)

        if args.merge:
            # Merge mode: combine with existing backup
            merge_file = Path(args.merge)
            if not merge_file.exists():
                raise FileNotFoundError(f"Backup file not found: {args.merge}")

            if not args.output_file:
                raise ValueError("Output file is required when using --merge mode")

            # Parse the input file first
            converter.converter.parse()

            # Merge with existing data
            merged_data = converter.converter.merge_with_existing_data(merge_file)

            # Save merged data
            with open(args.output_file, "w", encoding="utf-8") as f:
                json.dump(merged_data, f, indent=args.indent, ensure_ascii=False)
            print(
                f"Successfully merged {args.input_file} with {args.merge} and saved to {args.output_file}"
            )

            # Print merge summary
            new_tasks = len(converter.converter.tasks)
            total_tasks = len(merged_data["data"]["task"]["entities"])
            print("\nMerge Summary:")
            print(f"  New tasks added: {new_tasks}")
            print(f"  Total tasks: {total_tasks}")
            print(
                f"  Total projects: {len(merged_data['data']['project']['entities'])}"
            )
            print(f"  Total tags: {len(merged_data['data']['tag']['entities'])}")

        elif args.output_file:
            # Standard mode: convert and save to file
            converter.convert_to_file(args.output_file, args.indent)
        else:
            # Standard mode: convert and print to stdout
            data = converter.convert()
            print(json.dumps(data, indent=args.indent, ensure_ascii=False))

            # Print summary to stderr so it doesn't interfere with JSON output
            print("\nConversion Summary:", file=sys.stderr)
            print(f"  Tasks: {len(converter.converter.tasks)}", file=sys.stderr)
            print(f"  Projects: {len(converter.converter.projects)}", file=sys.stderr)
            print(f"  Tags: {len(converter.converter.tags)}", file=sys.stderr)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
