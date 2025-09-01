"""
Data models for Super Productivity JSON structure.

This module defines the data classes that match Super Productivity's JSON format.
Based on the plugin API types and the backup JSON structure.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Attachment:
    """
    Attachment model for tasks.

    Supports different types of attachments including links, images, and files.
    """

    id: str
    type: str  # "LINK", "IMG", "FILE"
    path: str
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert attachment to dictionary format for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class Task:
    """
    Task model compatible with Super Productivity format.

    Based on the Task interface from plugin API and backup JSON structure.
    """

    id: str
    title: str
    notes: str | None = None
    timeEstimate: int = 0  # milliseconds
    timeSpent: int = 0  # milliseconds
    isDone: bool = False
    projectId: str | None = None
    tagIds: list[str] = field(default_factory=list)
    parentId: str | None = None
    created: int = field(default_factory=lambda: int(time.time() * 1000))
    updated: int | None = None
    subTaskIds: list[str] = field(default_factory=list)

    # Additional fields for internal use
    timeSpentOnDay: dict[str, int] = field(default_factory=dict)
    doneOn: int | None = None
    attachments: list[Attachment] = field(default_factory=list)
    reminderId: str | None = None
    repeatCfgId: str | None = None

    # App-specific fields
    dueWithTime: int | None = None
    dueDay: str | None = None
    hasPlannedTime: bool | None = None
    modified: int | None = None

    # Issue tracking fields (optional)
    issueId: str | None = None
    issueProviderId: str | None = None
    issueType: Any | None = None
    issueWasUpdated: bool | None = None
    issueLastUpdated: int | None = None
    issueAttachmentNr: int | None = None
    issuePoints: int | None = None

    # UI state (internal)
    _hideSubTasksMode: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary format for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if key == "attachments" and isinstance(value, list):
                    # Convert Attachment objects to dictionaries
                    result[key] = [
                        attachment.to_dict()
                        if hasattr(attachment, "to_dict")
                        else attachment
                        for attachment in value
                    ]
                else:
                    result[key] = value
        return result


@dataclass
class WorklogExportSettings:
    """Worklog export settings configuration."""

    cols: list[str] = field(
        default_factory=lambda: [
            "DATE",
            "START",
            "END",
            "TIME_CLOCK",
            "TITLES_INCLUDING_SUB",
        ]
    )
    roundWorkTimeTo: int | None = None
    roundStartTimeTo: int | None = None
    roundEndTimeTo: int | None = None
    separateTasksBy: str = " | "
    groupBy: str = "DATE"


@dataclass
class Theme:
    """Theme configuration for projects and tags."""

    isAutoContrast: bool = True
    isDisableBackgroundGradient: bool = False
    primary: str = "#9ea03b"
    huePrimary: str = "500"
    accent: str = "#ff4081"
    hueAccent: str = "500"
    warn: str = "#e11826"
    hueWarn: str = "500"
    backgroundImageDark: str | None = None
    backgroundImageLight: str | None = None


@dataclass
class AdvancedConfig:
    """Advanced configuration for projects and tags."""

    worklogExportSettings: WorklogExportSettings = field(
        default_factory=WorklogExportSettings
    )


@dataclass
class Project:
    """
    Project model compatible with Super Productivity format.
    """

    id: str
    title: str
    theme: Theme = field(default_factory=Theme)
    isArchived: bool = False
    isHiddenFromMenu: bool = False
    isEnableBacklog: bool = True
    created: int | None = field(default_factory=lambda: int(time.time() * 1000))
    updated: int | None = None
    taskIds: list[str] = field(default_factory=list)
    backlogTaskIds: list[str] = field(default_factory=list)
    noteIds: list[str] = field(default_factory=list)
    advancedCfg: AdvancedConfig = field(default_factory=AdvancedConfig)
    icon: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert project to dictionary format for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "theme": self.theme.__dict__,
            "isArchived": self.isArchived,
            "isHiddenFromMenu": self.isHiddenFromMenu,
            "isEnableBacklog": self.isEnableBacklog,
            "created": self.created,
            "updated": self.updated,
            "taskIds": self.taskIds,
            "backlogTaskIds": self.backlogTaskIds,
            "noteIds": self.noteIds,
            "advancedCfg": {
                "worklogExportSettings": self.advancedCfg.worklogExportSettings.__dict__
            },
            "icon": self.icon,
        }


@dataclass
class Tag:
    """
    Tag model compatible with Super Productivity format.
    """

    id: str
    title: str
    color: str | None = None
    created: int = field(default_factory=lambda: int(time.time() * 1000))
    updated: int | None = None
    taskIds: list[str] = field(default_factory=list)
    icon: str | None = None
    theme: Theme = field(default_factory=Theme)
    advancedCfg: AdvancedConfig = field(default_factory=AdvancedConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert tag to dictionary format for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "color": self.color,
            "created": self.created,
            "updated": self.updated,
            "taskIds": self.taskIds,
            "icon": self.icon,
            "theme": self.theme.__dict__,
            "advancedCfg": {
                "worklogExportSettings": self.advancedCfg.worklogExportSettings.__dict__
            },
        }


def generate_id() -> str:
    """Generate a unique ID for tasks, projects, and tags."""
    return str(uuid.uuid4()).replace("-", "")[:21]


def generate_timestamp() -> int:
    """Generate current timestamp in milliseconds."""
    return int(time.time() * 1000)
