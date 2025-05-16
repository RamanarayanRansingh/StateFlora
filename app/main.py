from fastapi import FastAPI
from app.routers.chat import router

app = FastAPI(
    title="Flower Shop Chat Bot",
    version="3.0.0",
    description="API for Order management and approval"
)
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Flower Shop Chat Bot API"}
