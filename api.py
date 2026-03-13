"""
FastAPI server to serve news intelligence data.
"""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


app = FastAPI(
    title="News Intelligence API",
    description="API to serve processed whale migration news data",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEWS_OUTPUT_FILE = "data/news_output.json"


@app.get("/")
def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "News Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "/news": "Get processed news intelligence data",
            "/health": "Health check endpoint"
        }
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    file_exists = os.path.exists(NEWS_OUTPUT_FILE)

    return {
        "status": "healthy",
        "data_available": file_exists
    }


@app.get("/news")
def get_news():
    """
    Get processed news intelligence data.

    Returns:
        JSON object containing:
        - executive_summary: List of 5 executive bullet points
        - themes: List of identified themes
        - articles: List of articles with summaries and assigned themes
    """
    if not os.path.exists(NEWS_OUTPUT_FILE):
        raise HTTPException(
            status_code=404,
            detail=f"News data not found. Please run the pipeline first: python main.py"
        )

    try:
        with open(NEWS_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            news_data = json.load(f)

        return JSONResponse(content=news_data)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse news data. The file may be corrupted."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading news data: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("Starting News Intelligence API server...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")
    print("\nEndpoints:")
    print("  - GET /news - Get processed news data")
    print("  - GET /health - Health check")
    print("\nPress CTRL+C to stop the server\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
