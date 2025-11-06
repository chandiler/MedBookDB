# app/main.py
from contextlib import asynccontextmanager # Used to define asynchronous lifespan functions
from fastapi import FastAPI
from sqlalchemy import text # Allow execution of raw SQL queries
from .db import engine, init_db # Import engine and DB constructor from db module
from routes.admin_api import router as admin_router # Import admin router (backup / restore)

# Define lifespan event -> run when app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
        The lifespan function is used to manage the FastAPI application lifecycle.
        It runs initialization operations when the application starts (startup)
        and can clean up when it shuts down.
    """
    # Create tables in the database (if not existing)
    init_db()
    # Continue running other components of the application
    yield

app = FastAPI(
    title="Secure Healthcare Appointment System",
    lifespan=lifespan, # Attach the lifespan initialization function above
)

# Include the router APIs into the main application
app.include_router(admin_router)

# Define root endpoint "/" to test API working
@app.get("/")
def root():
    """
        Simple endpoint to test running application.
        Returns JSON confirming API works.
    """
    return {"message": "Healthcare System API running successfully"}

# Endpoint checks database connection status
@app.get("/health/db")
def health_db():
    """
        Test the connection to the database by executing a simple SQL query: SELECT 1.
        If there are no errors, return {"db": "ok"}.
    """
    # Open connection to DB
    with engine.connect() as conn:
        # Execute test SQL command
        conn.execute(text("SELECT 1"))
    # Return OK status if no error
    return {"db": "ok"}