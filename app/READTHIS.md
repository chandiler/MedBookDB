
# Backup & Recovery Module (PostgreSQL)

## Files
- `backup.py`  – create timestamped SQL dumps (`.sql.gz`) with rotation.
- `restore.py` – restore from the latest (or a specified) dump safely.

## Environment (.env)
```ini
DB_NAME=healthcare_system
DB_USER=postgres
DB_PASSWORD=****
DB_HOST=localhost
DB_PORT=5432
BACKUP_DIR=./backups
KEEP_DAYS=14
X-Admin-Token=supersecret-please-change
```

## Usage
```bash
# Create backup
python backup.py

# Override keep days for this run
python backup.py --keep 30

# Restore from latest
python restore.py --yes

# Restore from a specific file and drop schema first
python restore.py --file ./backups/medbookdb-YYYYmmddHHMMSS.sql.gz --drop-schema --yes
```

## Scheduling (cron, Linux/macOS)
```cron
# Every day at 02:30 local time
30 2 * * * /path/to/venv/bin/python /path/to/backup.py >> /path/to/backup.log 2>&1
```

## Scheduling (Windows Task Scheduler)
- Action: `Program/script` = python.exe
- Arguments: `C:\path\to\backup.py`
- Start in: `C:\path\to\project`

## Simulate crash & verify restore
1. **Take a fresh backup**: `python backup.py`
2. **Simulate data loss** (DEV ONLY): `psql -U <user> -d <db> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`
3. **Restore**: `python restore.py --yes`
4. **Validate**: run your smoke tests / sample queries to confirm counts and constraints.
