from fastapi import FastAPI

app = FastAPI(
    title="Banking Loan Eligibility Chatbot",
    description="AI-powered loan eligibility system",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Banking Loan Eligibility Chatbot API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }