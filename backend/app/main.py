from fastapi import FastAPI

app = FastAPI(
    title="FinAI Track API",
    description="Smart Personal Finance & AI Assistant Backend",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "FinAI Track API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

