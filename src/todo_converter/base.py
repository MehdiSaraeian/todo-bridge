"""
Base converter class for todo list formats.

This module provides the abstract base class for all todo list converters.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, cast

from .models import Project, Tag, Task


class BaseConverter(ABC):
    """
    Abstract base class for todo list converters.

    All converters should inherit from this class and implement the required methods.
    """

    def __init__(self, input_file: Path) -> None:
        """
        Initialize the converter with an input file.

        Args:
            input_file: Path to the input file to convert
        """
        self.input_file = input_file
        self.tasks: list[Task] = []
        self.projects: dict[str, Project] = {}
        self.tags: dict[str, Tag] = {}

        # Create default project for tasks without a project
        self._create_default_project()

    def _create_default_project(self) -> None:
        """Create a default 'Imported' project for tasks without explicit projects."""
        from .models import generate_id

        default_project = Project(id=generate_id(), title="Imported Tasks", icon="📥")
        self.projects["Imported Tasks"] = default_project

    @abstractmethod
    def parse(self) -> None:
        """
        Parse the input file and populate tasks, projects, and tags.

        This method should be implemented by each specific converter.
        """
        pass

    def _get_or_create_project(self, project_name: str) -> Project:
        """
        Get an existing project or create a new one.

        Args:
            project_name: Name of the project

        Returns:
            Project instance
        """
        if not project_name or project_name.strip() == "":
            project_name = "Imported Tasks"

        if project_name not in self.projects:
            from .models import generate_id

            project = Project(id=generate_id(), title=project_name, icon="📁")
            self.projects[project_name] = project

        return self.projects[project_name]

    def _get_or_create_tag(self, tag_name: str) -> Optional[Tag]:
        """
        Get existing tag or create a new one.

        Args:
            tag_name: Name of the tag

        Returns:
            Tag object or None if tag_name is empty
        """
        if not tag_name:
            return None

        # Check if tag already exists
        for tag in self.tags.values():
            if tag.title == tag_name:
                return tag

        # Create new tag
        from .models import generate_id

        tag = Tag(
            id=generate_id(),
            title=tag_name,
            color="#007acc",  # Default blue color
            created=int(time.time() * 1000),
            icon=None,
        )
        self.tags[tag.id] = tag
        return tag

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string and return in YYYY-MM-DD format.

        Args:
            date_str: Date string in various formats

        Returns:
            Date string in YYYY-MM-DD format or None if parsing fails
        """
        if not date_str or date_str.strip() == "":
            return None

        from datetime import datetime

        # Common date formats to try
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _parse_time_estimate(self, estimate_str: str) -> int:
        """
        Parse time estimate string and return milliseconds.

        Args:
            estimate_str: Time estimate string (e.g., "1h", "30m", "2h 30m")

        Returns:
            Time estimate in milliseconds
        """
        if not estimate_str or estimate_str.strip() == "":
            return 0

        estimate_str = estimate_str.strip().lower()
        total_ms = 0

        # Find hours
        hours_match = re.search(r"(\d+\.?\d*)\s*h", estimate_str)
        if hours_match:
            hours = float(hours_match.group(1))
            total_ms += int(hours * 60 * 60 * 1000)

        # Find minutes
        minutes_match = re.search(r"(\d+\.?\d*)\s*m", estimate_str)
        if minutes_match:
            minutes = float(minutes_match.group(1))
            total_ms += int(minutes * 60 * 1000)

        # If no units found, assume minutes
        if not hours_match and not minutes_match:
            try:
                minutes = float(estimate_str)
                total_ms = int(minutes * 60 * 1000)
            except ValueError:
                total_ms = 0

        return total_ms

    def get_super_productivity_data(self) -> dict[str, Any]:
        """
        Generate Super Productivity compatible JSON structure.

        Returns:
            Dictionary containing the complete Super Productivity data structure
        """
        # Create lookup dictionaries for O(1) access instead of O(n) loops
        project_lookup = {proj.id: proj for proj in self.projects.values()}
        tag_lookup = {tag.id: tag for tag in self.tags.values()}
        
        # Ensure all tasks are linked to their projects
        for task in self.tasks:
            if task.projectId and task.projectId in project_lookup:
                project = project_lookup[task.projectId]
                if task.id not in project.taskIds:
                    project.taskIds.append(task.id)

        # Ensure all tasks are linked to their tags
        for task in self.tasks:
            for tag_id in task.tagIds:
                if tag_id in tag_lookup:
                    tag = tag_lookup[tag_id]
                    if task.id not in tag.taskIds:
                        tag.taskIds.append(task.id)

        # Convert to dictionary format
        task_entities = {task.id: task.to_dict() for task in self.tasks}
        project_entities = {proj.id: proj.to_dict() for proj in self.projects.values()}
        tag_entities = {tag.id: tag.to_dict() for tag in self.tags.values()}

        current_time = int(self.tasks[0].created if self.tasks else time.time() * 1000)

        return {
            "data": {
                "task": {
                    "ids": list(task_entities.keys()),
                    "entities": task_entities,
                    "currentTaskId": None,
                    "selectedTaskId": list(task_entities.keys())[0]
                    if task_entities
                    else None,
                    "taskDetailTargetPanel": "Default",
                    "lastCurrentTaskId": None,
                    "isDataLoaded": True,
                },
                "project": {
                    "ids": list(project_entities.keys()),
                    "entities": project_entities,
                },
                "tag": {"ids": list(tag_entities.keys()), "entities": tag_entities},
                "timeTracking": {"project": {}, "tag": {}},
                "note": {"ids": [], "entities": {}, "todayOrder": []},
                "taskRepeatCfg": {"ids": [], "entities": {}},
                "reminders": [],
                "planner": {"days": {}},
                "simpleCounter": {"ids": [], "entities": {}},
                "boards": {"boardCfgs": []},
                "pluginUserData": [],
                "pluginMetadata": [],
                "globalConfig": {
                    "lang": {"lng": "en", "timeLocale": "en-US"},
                    "misc": {
                        "isConfirmBeforeExit": False,
                        "isConfirmBeforeExitWithoutFinishDay": True,
                        "isAutMarkParentAsDone": False,
                        "isTurnOffMarkdown": False,
                        "isAutoAddWorkedOnToToday": True,
                        "isMinimizeToTray": False,
                        "isTrayShowCurrentTask": True,
                        "isTrayShowCurrentCountdown": True,
                        "defaultProjectId": "INBOX_PROJECT",
                        "firstDayOfWeek": 1,
                        "startOfNextDay": 0,
                        "isUseMinimalNav": False,
                        "isDisableAnimations": False,
                        "isShowTipLonger": False,
                        "taskNotesTpl": "",
                        "isOverlayIndicatorEnabled": False,
                        "customTheme": "default",
                    },
                    "shortSyntax": {
                        "isEnableProject": True,
                        "isEnableDue": True,
                        "isEnableTag": True,
                    },
                    "evaluation": {"isHideEvaluationSheet": False},
                    "idle": {
                        "isOnlyOpenIdleWhenCurrentTask": False,
                        "isEnableIdleTimeTracking": True,
                        "minIdleTime": 300000,
                    },
                    "takeABreak": {
                        "isTakeABreakEnabled": False,
                        "isLockScreen": False,
                        "isTimedFullScreenBlocker": False,
                        "timedFullScreenBlockerDuration": 8000,
                        "isFocusWindow": False,
                        "takeABreakMessage": "",
                        "takeABreakMinWorkingTime": 3600000,
                        "takeABreakSnoozeTime": 900000,
                        "motivationalImgs": [],
                    },
                    "dominaMode": {
                        "isEnabled": False,
                        "interval": 300000,
                        "volume": 75,
                        "text": "",
                        "voice": None,
                    },
                    "focusMode": {
                        "isAlwaysUseFocusMode": False,
                        "isSkipPreparation": False,
                    },
                    "pomodoro": {
                        "isEnabled": False,
                        "duration": 1500000,
                        "breakDuration": 300000,
                        "longerBreakDuration": 900000,
                        "cyclesBeforeLongerBreak": 4,
                        "isStopTrackingOnBreak": True,
                        "isStopTrackingOnLongBreak": True,
                        "isManualContinue": False,
                        "isManualContinueBreak": False,
                        "isPlaySound": False,
                        "isPlaySoundAfterBreak": False,
                        "isPlayTick": False,
                    },
                    "keyboard": {},
                    "localBackup": {"isEnabled": True},
                    "sound": {
                        "volume": 75,
                        "isIncreaseDoneSoundPitch": True,
                        "doneSound": "ding-small-bell.mp3",
                        "breakReminderSound": None,
                        "trackTimeSound": None,
                    },
                    "timeTracking": {
                        "trackingInterval": 1000,
                        "defaultEstimate": 0,
                        "defaultEstimateSubTasks": 0,
                        "isNotifyWhenTimeEstimateExceeded": True,
                        "isAutoStartNextTask": False,
                        "isTrackingReminderEnabled": False,
                        "isTrackingReminderShowOnMobile": False,
                        "trackingReminderMinTime": 300000,
                        "isTrackingReminderNotify": False,
                        "isTrackingReminderFocusWindow": False,
                    },
                    "reminder": {
                        "isCountdownBannerEnabled": True,
                        "countdownDuration": 600000,
                    },
                    "schedule": {
                        "isWorkStartEndEnabled": False,
                        "workStart": "9:00",
                        "workEnd": "17:00",
                        "isLunchBreakEnabled": False,
                        "lunchBreakStart": "13:00",
                        "lunchBreakEnd": "14:00",
                    },
                    "sync": {
                        "isEnabled": False,
                        "isCompressionEnabled": False,
                        "isEncryptionEnabled": False,
                        "encryptKey": None,
                        "syncProvider": None,
                        "syncInterval": 60000,
                        "webDav": {
                            "baseUrl": None,
                            "userName": None,
                            "password": None,
                            "syncFolderPath": "super-productivity",
                        },
                        "localFileSync": {"syncFolderPath": ""},
                    },
                },
                "issueProvider": {"ids": [], "entities": {}},
                "metric": {"ids": [], "entities": {}},
                "improvement": {
                    "ids": [],
                    "entities": {},
                    "hideDay": None,
                    "hiddenImprovementBannerItems": [],
                },
                "obstruction": {"ids": [], "entities": {}},
                "archiveYoung": {
                    "task": {"ids": [], "entities": {}},
                    "timeTracking": {"project": {}, "tag": {}},
                    "lastTimeTrackingFlush": current_time,
                    "lastFlush": current_time,
                },
                "archiveOld": {
                    "task": {"ids": [], "entities": {}},
                    "timeTracking": {"project": {}, "tag": {}},
                    "lastTimeTrackingFlush": current_time,
                },
            },
            "crossModelVersion": 4.2,
            "lastUpdate": current_time,
            "timestamp": current_time,
        }

    def merge_with_existing_data(self, existing_backup_file: Path) -> dict[str, Any]:
        """
        Merge converted tasks with existing Super Productivity backup data.

        Args:
            existing_backup_file: Path to existing Super Productivity backup JSON file

        Returns:
            Dictionary containing merged Super Productivity data structure
        """
        # Load existing backup data
        try:
            with open(existing_backup_file, encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Failed to load existing backup file {existing_backup_file}: {e}"
            )

        # Validate it's a Super Productivity backup
        if "data" not in existing_data or "task" not in existing_data["data"]:
            raise ValueError("Invalid Super Productivity backup file format")

        # Get existing entities
        existing_tasks = existing_data["data"]["task"]["entities"]
        existing_projects = existing_data["data"]["project"]["entities"]
        existing_tags = existing_data["data"]["tag"]["entities"]

        # Prepare our new data
        self._prepare_for_merge()
        new_project_entities = {
            proj.id: proj.to_dict() for proj in self.projects.values()
        }
        new_tag_entities = {tag.id: tag.to_dict() for tag in self.tags.values()}

        # Merge projects (avoid duplicates by title)
        merged_projects = existing_projects.copy()
        project_title_to_id = {
            proj["title"]: proj_id for proj_id, proj in existing_projects.items()
        }

        for new_proj_id, new_proj in new_project_entities.items():
            if new_proj["title"] in project_title_to_id:
                # Project exists, update tasks to use existing project ID
                existing_proj_id = project_title_to_id[new_proj["title"]]
                # Add new tasks to existing project's task list BEFORE reassigning
                if existing_proj_id in merged_projects:
                    for task in self.tasks:
                        if task.projectId == new_proj_id:
                            if (
                                task.id
                                not in merged_projects[existing_proj_id]["taskIds"]
                            ):
                                merged_projects[existing_proj_id]["taskIds"].append(
                                    task.id
                                )
                # Now reassign the project IDs
                self._reassign_tasks_to_existing_project(new_proj_id, existing_proj_id)
            else:
                # New project, add it
                merged_projects[new_proj_id] = new_proj

        # Merge tags (avoid duplicates by title)
        merged_tags = existing_tags.copy()
        tag_title_to_id = {
            tag["title"]: tag_id for tag_id, tag in existing_tags.items()
        }

        for new_tag_id, new_tag in new_tag_entities.items():
            if new_tag["title"] in tag_title_to_id:
                # Tag exists, update tasks to use existing tag ID
                existing_tag_id = tag_title_to_id[new_tag["title"]]
                # Add new tasks to existing tag's task list BEFORE reassigning
                if existing_tag_id in merged_tags:
                    for task in self.tasks:
                        if new_tag_id in task.tagIds:
                            if task.id not in merged_tags[existing_tag_id]["taskIds"]:
                                merged_tags[existing_tag_id]["taskIds"].append(task.id)
                # Now reassign the tag IDs
                self._reassign_tasks_to_existing_tag(new_tag_id, existing_tag_id)
            else:
                # New tag, add it
                merged_tags[new_tag_id] = new_tag

        # Regenerate task entities with updated project/tag IDs
        updated_task_entities = {task.id: task.to_dict() for task in self.tasks}

        # Merge tasks (new tasks are always added)
        merged_tasks = existing_tasks.copy()
        merged_tasks.update(updated_task_entities)

        # Update the data structure
        current_time = int(time.time() * 1000)

        merged_data: dict[str, Any] = cast(dict[str, Any], existing_data.copy())
        merged_data["data"]["task"]["ids"] = list(merged_tasks.keys())
        merged_data["data"]["task"]["entities"] = merged_tasks
        merged_data["data"]["project"]["ids"] = list(merged_projects.keys())
        merged_data["data"]["project"]["entities"] = merged_projects
        merged_data["data"]["tag"]["ids"] = list(merged_tags.keys())
        merged_data["data"]["tag"]["entities"] = merged_tags
        merged_data["lastUpdate"] = current_time
        merged_data["timestamp"] = current_time

        return merged_data

    def _prepare_for_merge(self) -> None:
        """Prepare tasks for merging by ensuring proper linkages."""
        # Create lookup dictionaries for O(1) access instead of O(n) loops
        project_lookup = {proj.id: proj for proj in self.projects.values()}
        tag_lookup = {tag.id: tag for tag in self.tags.values()}
        
        # Ensure all tasks are linked to their projects
        for task in self.tasks:
            if task.projectId and task.projectId in project_lookup:
                project = project_lookup[task.projectId]
                if task.id not in project.taskIds:
                    project.taskIds.append(task.id)

        # Ensure all tasks are linked to their tags
        for task in self.tasks:
            for tag_id in task.tagIds:
                if tag_id in tag_lookup:
                    tag = tag_lookup[tag_id]
                    if task.id not in tag.taskIds:
                        tag.taskIds.append(task.id)

    def _reassign_tasks_to_existing_project(
        self, old_project_id: str, new_project_id: str
    ) -> None:
        """Reassign tasks from a new project to an existing project."""
        for task in self.tasks:
            if task.projectId == old_project_id:
                task.projectId = new_project_id

    def _reassign_tasks_to_existing_tag(self, old_tag_id: str, new_tag_id: str) -> None:
        """Reassign tasks from a new tag to an existing tag."""
        for task in self.tasks:
            if old_tag_id in task.tagIds:
                task.tagIds = [
                    new_tag_id if tid == old_tag_id else tid for tid in task.tagIds
                ]
