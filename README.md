# Super Productivity Todo List Converter

A Python tool to convert todo lists from various formats (CSV, Markdown) to Super Productivity JSON format for easy import.

## Features

- **CSV Support**: Convert CSV files with customizable columns
- **Markdown Support**: Convert Markdown task lists with full hierarchy support
- **Project Organization**: Automatically creates projects from headers or CSV project columns
- **Tag Support**: Handle tags from CSV columns or hashtags in Markdown
- **Time Estimates**: Parse time estimates in various formats (1h, 30m, 2h 30m)
- **Due Dates**: Support multiple date formats and due date specifications
- **Subtasks**: Handle nested tasks and subtask relationships
- **Complete Import Compatibility**: Generate full Super Productivity JSON structure with all required sections
- **Merge Mode**: Append new tasks to existing Super Productivity backups without overwriting data
- **Smart Deduplication**: Automatically merge into existing projects and tags by name

## Installation

1. Clone or download this repository
2. Install dependencies (optional, for development):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Command Line Interface

You can run the tool directly from the repository using `python -m src.todo_converter` or, if installed, simply `todo-bridge`.

```bash
# Convert CSV to JSON file
python -m src.todo_converter input_file.csv output_file.json

# Convert Markdown to JSON file  
python -m src.todo_converter input_file.md output_file.json
  
# Merge new tasks into existing Super Productivity backup:
python -m src.todo_converter new_tasks.csv --merge backup.json merged_backup.json
python -m src.todo_converter daily_todos.md --merge super-productivity-backup.json updated_backup.json

# Output to stdout (for piping)
python -m src.todo_converter input_file.csv

# Custom JSON formatting
python -m src.todo_converter input_file.csv output_file.json --indent 4
```

### Python API

```python
from src.todo_converter import TodoConverter

# Create converter
converter = TodoConverter('my_todos.csv')

# Convert to dictionary
data = converter.convert()

# Convert and save to file
converter.convert_to_file('super_productivity_import.json')
```

## Supported Formats

### CSV Format

Expected columns (all optional except `title`):

- `title`: Task title (required)
- `notes`: Task notes
- `project`: Project name
- `tags`: Comma-separated tags
- `isDone`: Completion status (true/false, 1/0, yes/no)
- `timeEstimate`: Time estimate (1h, 30m, 2h 30m, etc.)
- `created`: Creation date (YYYY-MM-DD or MM/DD/YYYY)
- `modified`: Modification date
- `dueDay`: Due date
- `dueWithTime`: Due date with time (ISO format)
- `remindAt`: Reminder time
- `subtasks`: Pipe-separated subtask titles (Subtask 1|Subtask 2)

#### Example CSV

```csv
title,notes,project,tags,isDone,timeEstimate,dueDay,subtasks
"Complete project proposal","Review and finalize","Work","urgent,important",false,"2h","2023-12-31","Research|Write draft|Review"
"Buy groceries","","Personal","shopping",false,"30m","2023-12-25",""
"Meeting with team","Discuss Q4 goals","Work","meeting",true,"1h","",""
```

### Markdown Format

Supports various Markdown todo list formats:

#### Basic Task Lists
```markdown
# Project Name

- [ ] Incomplete task
- [x] Completed task
- [ ] Task with notes

## Another Project

- [ ] Another task
```

#### Nested Tasks (Subtasks)
```markdown
# Main Project

- [ ] Main task
  - [ ] Subtask 1
  - [ ] Subtask 2
    - [ ] Sub-subtask
- [ ] Another main task
```

#### Tags and Time Estimates
```markdown
# Tagged Tasks

- [ ] Task with #urgent and #work tags
- [ ] Task with time estimate (2h)
- [ ] Task with due date @due:2023-12-31
- [ ] Complex task (1h 30m) #important @2023-12-25
```

#### Supported Markdown Features

- **Headers**: `#`, `##`, `###` etc. create projects
- **Task Lists**: `- [ ]`, `- [x]`, `* [ ]`, `+ [ ]`, `1. [ ]`
- **Checkboxes**: `[ ]` (incomplete), `[x]` or `[X]` (complete)
- **Tags**: `#hashtag` format
- **Time Estimates**: `(1h)`, `(30m)`, `(2h 30m)` in parentheses
- **Due Dates**: `@due:YYYY-MM-DD`, `@YYYY-MM-DD`, `due: MM/DD/YYYY`
- **Bold Text**: `**bold**` converted to notes
- **Nested Lists**: Indentation creates subtask hierarchy

## Output Format

The converter generates a Super Productivity JSON structure with 19 required sections for successful import:

```json
{
  "data": {
    "task": {
      "ids": ["task-id-1", "task-id-2"],
      "entities": {
        "task-id-1": {
          "id": "task-id-1", 
          "title": "Task Title",
          "notes": "Task notes",
          "timeEstimate": 3600000,
          "timeSpent": 0,
          "isDone": false,
          "projectId": "project-id-1",
          "tagIds": ["tag-id-1"],
          "created": 1703721600000,
          "subTaskIds": []
        }
      }
    },
    "project": { /* ... */ },
    "tag": { /* ... */ },
    "timeTracking": { /* ... */ },
    "globalConfig": { /* ... */ },
    "boards": { /* ... */ },
    "reminders": [],
    "planner": { /* ... */ },
    "simpleCounter": { /* ... */ },
    "note": { /* ... */ },
    "taskRepeatCfg": { /* ... */ },
    "pluginUserData": [],
    "pluginMetadata": [],
    "issueProvider": { /* ... */ },
    "metric": { /* ... */ },
    "improvement": { /* ... */ },
    "obstruction": { /* ... */ },
    "archiveYoung": { /* ... */ },
    "archiveOld": { /* ... */ }
  },
  "crossModelVersion": 4.2,
  "lastUpdate": 1703721600000,
  "timestamp": 1703721600000
}
```

### Merge Mode

When using `--merge`, the converter intelligently combines new tasks with existing data:

- **Existing Projects**: New tasks are added to projects with matching names
- **New Projects**: Created when no match is found
- **Existing Tags**: Reused for tasks with matching tag names  
- **New Tags**: Created as needed
- **Data Preservation**: All existing tasks, settings, and metadata are preserved
- **No Overwrites**: Only additive operations, never deletes or modifies existing data

## Examples

### Converting the Sample Files

The repository includes sample files you can test with:

```bash
# Convert the sample CSV (creates new backup)
python -m src.todo_converter to-do_list.csv converted_csv.json

# Convert the sample Markdown (creates new backup)
python -m src.todo_converter to-do_list.md converted_md.json

# Merge sample CSV into existing backup
python -m src.todo_converter to-do_list.csv merged_backup.json --merge super-productivity-backup.json
```

### Import to Super Productivity

#### Option 1: Full Import (Replace All Data)
1. Run the converter without `--merge` to generate a JSON file
2. Open Super Productivity  
3. Go to Settings → Sync
4. Use the import functionality to load your JSON file
5. ⚠️ **Warning**: This replaces all existing data

#### Option 2: Merge Import (Add to Existing Data)
1. First, export your current Super Productivity data as a backup
2. Run the converter with `--merge backup.json` to append new tasks
3. Import the merged JSON file
4. ✅ **Safe**: Preserves existing data and adds new tasks

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run tests with coverage
python -m pytest tests/ --cov=src/todo_converter
```

### Code Quality

```bash
# Format code with Ruff
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
todo-converter/
├── src/
│   └── todo_converter/
│       ├── __init__.py
│       ├── __main__.py
│       ├── models.py          # Data models
│       ├── base.py            # Base converter class
│       ├── csv_converter.py   # CSV converter
│       ├── markdown_converter.py  # Markdown converter
│       └── converter.py       # Main converter interface
├── tests/
│   ├── test_csv_converter.py
│   └── test_markdown_converter.py
├── convert_todos.py           # CLI script
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for any new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is provided as-is for converting todo lists to Super Productivity format. Feel free to modify and distribute as needed.

## Troubleshooting

### Common Issues

1. **Import fails**: Ensure you're using the complete JSON structure (all 19 sections)
2. **Empty output**: Check that your input file has the correct format and required columns/fields
3. **Encoding errors**: Ensure your input files are saved in UTF-8 encoding
4. **Date parsing errors**: Use supported date formats (YYYY-MM-DD recommended)
5. **Missing tasks**: Check for empty titles or malformed rows/lines
6. **Merge conflicts**: Project/tag names are case-sensitive ("Work" ≠ "work")

### Getting Help

- Check the test files for examples of supported formats
- Review the sample input files included in the repository
- Ensure your input files match the expected format specifications
