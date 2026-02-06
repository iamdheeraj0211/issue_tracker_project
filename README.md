# Issue Tracker API

A robust RESTful API for tracking issues, managing tasks, and generating reports, built with Django and Django REST Framework.

## Features
- **User Authentication**: Token-based signup and signin.
- **Issue Management**: Create, read, update, delete (CRUD) issues.
    - **Optimistic Concurrency Control**: Prevents overwrite conflicts using versioning.
    - **Bulk Operations**: Update status for multiple issues at once.
    - **CSV/Excel Import**: Bulk import issues from files.
- **Labels & Comments**: Organize issues with labels and discuss via comments.
- **Reports**: Analyze top assignees and issue resolution latency.
- **Database**: Configured for PostgreSQL (Cloud/Local) with automatic failover/fallback logic.

## Tech Stack
- **Backend**: Django 5.2, Django REST Framework
- **Database**: PostgreSQL (Neon/Local)
- **Data Processing**: Pandas (for file imports)
- **Utilities**: Python-dotenv (env management)

## Setup Instructions

### 1. Clone the repository
```bash
git clone <repo_url>
cd issue_tracker
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in `issue_tracker/issue_tracker/` with the following variables:

```ini
# Primary (Neon Cloud DB) - Optional
DB_ENGINE=django.db.backends.postgresql
DB_NAME=issue_tracker_db
DB_USER=<your_user>
DB_PASSWORD=<your_password>
DB_HOST=<your_host>
DB_PORT=5432
DB_SSLMODE=require

# Secondary (Local DB) - Optional
SEC_DB_ENGINE=django.db.backends.postgresql
SEC_DB_NAME=issue_tracker_db
SEC_DB_USER=postgres
SEC_DB_PASSWORD=root
SEC_DB_HOST=localhost
SEC_DB_PORT=5432
```
*Note: If no env vars are set, the project defaults to SQLite for easy local development.*

### 5. Run Migrations
```bash
cd issue_tracker
python manage.py migrate
```

### 6. Run the Server
```bash
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /signup/` - Register a new user
- `POST /signin/` - Login and get token

### Issues
- `GET /issues` - List issues (supports filters: `id`, `keyword`)
- `POST /issues` - Create a new issue
- `GET /issues/{id}` - Retrieve details
- `PATCH /issues/{id}` - Update issue (**Requires `version` field** for concurrency check)
- `DELETE /issues/{id}` - Delete issue
- `POST /issues/import` - Bulk import from CSV/Excel
- `POST /issues/bulk-status` - Bulk update status

### Import File Format (CSV/Excel)
The `/issues/import` endpoint accepts `.csv` or `.xlsx` files. The file **must** contain the following columns:

| Column Name | Type | Required | Description |
|-------------|------|----------|-------------|
| `title` | Text | Yes | The title of the issue. |
| `description` | Text | Yes | Detailed description of the issue. |
| `status` | Text | Yes | Must be one of: `open`, `in_progress`, `resolved`. |
| `labels` | Text | Yes | Comma-separated list of existing label names (e.g., "bug,urgent"). |
| `assignee` | Text | No | Username of the assignee (must exist in the system). |

**Example Row:**
```csv
title,description,status,labels,assignee
"Login Bug","Cannot login with email","open","bug,high priority","john_doe"
```

### Labels & Comments
- `GET /labels/` - List labels
- `POST /labels/` - Create label
- `POST /issues/{id}/comments` - Add comment
- `PUT /issues/{id}/labels` - Replace labels for an issue

### Reports
- `GET /reports/top-assignees` - View most active assignees
- `GET /reports/latency` - Average time to resolve issues

## Optimistic Concurrency Control (OCC)
To prevent lost updates when multiple users edit the same issue:
1. **Fetch**: `GET /issues/1` -> returns `{"id": 1, "version": 5, ...}`
2. **Update**: Send `PATCH /issues/1` with `{"version": 5, "status": "resolved"}`.
3. **Result**:
   - **Success (200)**: If server version is 5. New version becomes 6.
   - **Conflict (409)**: If server version is already 6 (changed by someone else). User must reload and re-apply changes.
