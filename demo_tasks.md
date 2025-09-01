# Demo - Todo Bridge Feature Showcase

This demo demonstrates all supported features of the todo-bridge converter.

## 📝 Basic Task Features
- [x] Completed checkbox task (1h) #basic
- [ ] Incomplete checkbox task (2h) #basic
- [ ] No time estimate task #basic  
- [ ] Multiple #tags #and #time (3h 45m) #basic

## ⏰ Time Tracking Features
- [x] Auto time tracking (2h) #auto-tracking
- [x] Explicit logged time (1h) @logged:45m #explicit
- [x] Date-specific tracking (30m) @worked:25m@2025-08-28 #date-specific
- [ ] Future time planning (3h) @spent:2h@2025-09-01 #planning

## 📅 Due Dates
- [ ] ISO format @due:2024-02-15T14:30 #iso-date
- [ ] US format @due:12/31/2024 #us-date
- [ ] Simple format due:2024-01-30 #simple-date

## 📎 Attachments
- [ ] Web link (1h) @link:https://example.com "Documentation" #link
- [ ] File attachment (30m) @file:/path/file.pdf "Spec" #file  
- [ ] Image reference (15m) @img:https://example.com/image.png "Diagram" #image
- [ ] Multiple attachments (2h) @link:https://api.docs "API" @file:/schema.json "Schema" #multiple

## 🏗️ Hierarchy & Notes
- [ ] Parent with subtasks (6h) #hierarchy #parent
  This parent task has detailed notes explaining the work.
  
  **Important considerations:**
  - Quality standards must be maintained
  - Testing is required for all components
  
  - [ ] First subtask (2h) #subtask
    Subtask-specific notes here.
  - [ ] Second subtask (3h) #subtask  
    - [ ] This deep item stays as markdown in notes
    - [ ] Another deep item with details
      - [ ] level-4 task
        - [ ] level-5 task
  - [ ] Third subtask (1h) #subtask
  
  Additional notes after subtasks are preserved.

## 🚀 Project Setup
- [x] Research technology stack (2h) #planning #research @logged:2h@2025-08-30
- [ ] Build main feature (4h) #development @due:2024-01-25
  - [ ] API implementation (2h) #backend #api
  - [ ] UI components (1h 30m) #frontend #ui
  - [ ] Testing suite (30m) #testing
- [x] Bug fix with tracking (45m) #bugfix @spent:30m@2025-08-29
- [ ] Documentation (1h 30m) #docs @file:/specs/requirements.pdf "Requirements"

## 🎯 Mixed Content Examples
- [ ] Task with **bold extraction** and formatting (1h) #bold #formatting
  Regular notes content with **important highlights**.
  
  - [ ] Notes-generated subtask (45m) #notes-subtask
  
  More content after the subtask list.

## 📊 Edge Cases & Formats
* [ ] Asterisk bullet format (1h) #bullet-style
+ [ ] Plus bullet format (30m) #bullet-style  
1. [ ] Numbered list format (45m) #numbered
- [ ] Special chars!@#$%^&*() and "quotes" (15m) #special-chars
- [ ] Time variations: (2hours 30minutes) vs (1.5h) vs (90m) #time-formats

## 🔄 Complex Hierarchy Test
- [ ] Multi-level parent (8h) #complex #hierarchy
  - [ ] Level 1 child A (3h) #child
    - [ ] Level 2 stays as markdown
      - [ ] Level 3 preserved in notes  
  - [ ] Level 1 child B (5h) #child
    - [ ] Another level 2 item
  - [x] Completed child (45m) #child #completed

