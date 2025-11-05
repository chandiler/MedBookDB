# 🏥 Secure Healthcare Appointment System

A backend project for managing healthcare appointments with a focus on **database security**, **transaction control**, and **backup & recovery**.  
Developed in **Python (FastAPI + SQLAlchemy)** for the *Advanced Database Topics* course.

---

## 📦 Features
- **Authentication & Authorization** — Secure login using bcrypt and JWT  
- **Role Management** — Patients, Doctors, and Admins with different permissions  
- **Transactional Integrity** — Atomic operations with rollback on failure  
- **Backup & Recovery** — Automated SQL dump and restore simulation  
- **SQL Injection Prevention** — Input validation and prepared statements  

---

## ⚙️ Setup Instructions

### 🪟 For Windows
```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

🍎 For macOS / Linux
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

🚀 Run the Server
uvicorn app.main:app --reload


Then open your browser at:
👉 http://127.0.0.1:8000

API documentation (Swagger UI):
👉 http://127.0.0.1:8000/docs

🧱 Project Structure
secure_healthcare_system/
├── app/
│   ├── __init__.py
│   └── main.py
│   └── ... (routes, models, etc.)
│
├── requirements.txt
├── .gitignore
└── README.md

👥 Team Collaboration

Don’t push the venv/ folder or .env files.

After cloning, each member runs:

python -m venv venv
source venv/bin/activate      # or venv\Scripts\activate on Windows
pip install -r requirements.txt


Use branches or pull requests for individual features.

🧪 Testing

To verify your setup:

uvicorn app.main:app --reload


You should see:

Uvicorn running on http://127.0.0.1:8000


and be able to access the Swagger API docs at /docs.
```

# Database Migrations (Alembic)


```bash
# If there is no baseline yet
alembic revision -m "baseline"

# Apply all migrations (creates tables, e.g., users)
alembic upgrade head

```