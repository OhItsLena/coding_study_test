# Study Flow Logging System Implementation

## Overview

A comprehensive logging system has been implemented to track participant transitions through the study flow. The system records timestamps for first visits to key routes and stores logs in JSON format in a separate logging branch to keep them hidden from participants.

## Key Features

### 1. **Separate Logging Repository Structure**
- Logs are stored in a separate directory: `logs-{participant_id}/`
- Uses a dedicated `logging` git branch to keep logs separate from main work
- Each participant gets their own isolated logging space

### 2. **JSON Log Format**
Each log entry contains:
```json
{
  "participant_id": "participant-123",
  "route": "task",
  "study_stage": 1,
  "timestamp": "2025-06-12T15:04:36.499242",
  "timestamp_unix": 1749733476.499242,
  "development_mode": true,
  "session_data": {
    "coding_session_start": true,
    "current_task": 1,
    "coding_condition": "ai-assisted"
  }
}
```

### 3. **Logged Routes and Events**

#### **Study Flow Routes:**
- `home` - Initial landing page
- `background_questionnaire` - Background survey access
- `tutorial` - Tutorial page access
- `welcome_back` - Stage 2 return page
- `task` - Coding task page (critical transition)
- `ux_questionnaire` - Final UX survey

#### **Special Events:**
- `task_completion_{id}` - When individual tasks are completed
- `timer_expired` - When 40-minute timer expires

### 4. **Session-Based Duplicate Prevention**
- Only logs the **first visit** to each route per stage
- Uses Flask session to track which routes have been logged
- Prevents duplicate entries while allowing legitimate re-visits

### 5. **Stage-Aware Logging**
- Separate tracking for Stage 1 and Stage 2
- Same route can be logged once per stage
- Stage transitions are captured with context

## Implementation Details

### Core Functions

#### `log_route_visit()`
Main logging function that:
- Checks if this is first visit to route
- Creates timestamped JSON log entry
- Commits to git with descriptive message
- Optionally pushes to remote repository

#### `should_log_route()` / `mark_route_as_logged()`
Session management functions that:
- Track which routes have been visited
- Prevent duplicate logging
- Maintain state per study stage

#### `ensure_logging_repository()`
Repository setup function that:
- Creates logging directory structure
- Initializes git repository
- Sets up logging branch
- Creates initial README

### Integration Points

#### Flask Route Integration
Each major route now includes logging:
```python
if should_log_route(session, 'route_name', study_stage):
    log_route_visit(
        participant_id=participant_id,
        route_name='route_name',
        development_mode=DEVELOPMENT_MODE,
        study_stage=study_stage,
        session_data=relevant_context,
        github_token=GITHUB_TOKEN,
        github_org=GITHUB_ORG
    )
    mark_route_as_logged(session, 'route_name', study_stage)
```

## File Structure

```
logs-{participant_id}/
├── .git/                    # Git repository
│   └── logs/               # Git internal logs
├── README.md               # Repository description
└── route_visits.json       # Main log file
```

## Benefits

1. **Research Value**: Precise timestamps for analyzing study flow patterns
2. **Hidden from Participants**: Stored in separate directory/branch
3. **Comprehensive Coverage**: Tracks all major transitions and events
4. **Duplicate Prevention**: Only logs meaningful first visits
5. **Stage Awareness**: Handles multi-stage study design
6. **Git Integration**: Full audit trail with commit history
7. **Remote Backup**: Can push logs to GitHub for backup/analysis

## Testing Results

The implementation has been tested and verified:
- ✅ Log directory creation
- ✅ Git repository initialization with logging branch
- ✅ JSON log file creation and updates
- ✅ Route visit logging with timestamps
- ✅ Session-based duplicate prevention
- ✅ Stage-specific logging (Stage 1 vs Stage 2)
- ✅ Git commit history with descriptive messages
- ✅ Task completion and timer expiration events

## Usage in Analysis

Researchers can analyze the logs to understand:
- Time spent on tutorial vs jumping to tasks
- Patterns in task completion timing
- Stage transition behaviors
- Drop-off points in the study flow
- Differences between AI-assisted vs manual coding conditions

The JSON format makes it easy to import into analysis tools like Python pandas, R, or statistical software.
