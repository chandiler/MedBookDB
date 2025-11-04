from fastapi import FastAPI

app = FastAPI(title="Secure Healthcare Appointment System")

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully"}
