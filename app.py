"""
FastAPI server to serve news intelligence data.
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from anthropic import Anthropic

from airtable_client import (
    get_all_articles, get_all_runs, get_most_recent_run, get_articles_by_run,
    update_run_themes, update_article_theme, update_executive_summary
)
from main import run_news_pipeline

# Load environment variables
load_dotenv()


app = FastAPI(
    title="News Intelligence API",
    description="API to serve processed whale migration news data",
    version="1.0.0"
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEWS_OUTPUT_FILE = "data/news_output.json"

# LLM provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "claude"


def call_llm(prompt: str, max_tokens: int = 300) -> str:
    """
    Call LLM with the given prompt using configured provider.

    Args:
        prompt: The prompt to send to the LLM
        max_tokens: Maximum tokens in response

    Returns:
        LLM response text
    """
    if LLM_PROVIDER == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes news articles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    elif LLM_PROVIDER == "claude":
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()

    else:
        raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")


def derive_themes_from_articles(articles: List[Dict]) -> List[str]:
    """
    Use LLM to derive 3-5 themes from article summaries.

    Args:
        articles: List of article records from Airtable

    Returns:
        List of theme strings (max 5)
    """
    # Extract summaries
    summaries = []
    for article in articles:
        summary = article['fields'].get('Summary', '')
        if summary:
            summaries.append(summary)

    if not summaries:
        return []

    # Create prompt
    summaries_text = "\n\n".join([f"- {summary}" for summary in summaries[:50]])  # Limit to 50 to avoid token limits

    prompt = f"""Analyze the following article summaries about whale migration and identify 3-5 recurring themes or topics.

Return ONLY a numbered list of themes, one per line. Example format:
1. Migration Patterns
2. Climate Impact

Summaries:
{summaries_text}"""

    response = call_llm(prompt, max_tokens=500)

    # Parse themes from response
    themes = []
    for line in response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # Remove numbering, bullets, etc.
        line = line.lstrip('0123456789.-•*) ')
        if line:
            themes.append(line)

    return themes[:5]  # Limit to 5 themes maximum


def count_theme_mentions(theme: str, articles: List[Dict]) -> int:
    """
    Use LLM to count how many articles relate to a given theme.

    Args:
        theme: The theme to check for
        articles: List of article records from Airtable

    Returns:
        Count of articles that relate to the theme
    """
    # For efficiency, batch articles and ask LLM to identify which ones relate
    summaries_with_ids = []
    for i, article in enumerate(articles):
        summary = article['fields'].get('Summary', '')
        if summary:
            summaries_with_ids.append(f"{i}. {summary[:200]}")  # Truncate summaries to save tokens

    if not summaries_with_ids:
        return 0

    summaries_text = "\n\n".join(summaries_with_ids)

    prompt = f"""Theme: "{theme}"

Review these article summaries and identify which ones relate to the theme above. An article relates to the theme if it discusses, mentions, or is relevant to that topic.

Return ONLY the numbers of articles that relate to the theme, separated by commas. Example: 0,3,7,12

Article Summaries:
{summaries_text}"""

    response = call_llm(prompt, max_tokens=200)

    # Parse the numbers from response
    try:
        # Extract numbers from response
        numbers = []
        for part in response.replace(' ', '').split(','):
            part = part.strip()
            if part.isdigit():
                numbers.append(int(part))
        return len(numbers)
    except:
        # If parsing fails, fall back to simple keyword matching
        count = 0
        for article in articles:
            summary = article['fields'].get('Summary', '').lower()
            if theme.lower() in summary:
                count += 1
        return count


@app.get("/")
def index():
    """
    Serve the frontend dashboard.
    """
    return FileResponse("static/index.html")


@app.get("/api")
def api_info():
    """
    API information endpoint.
    """
    return {
        "message": "News Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "/": "Frontend dashboard",
            "/api": "API information",
            "/news": "Get processed news intelligence data (from JSON file)",
            "/dashboard": "Get real-time dashboard data (from Airtable)",
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


@app.get("/dashboard")
def get_dashboard():
    """
    Get dashboard data from most recent run (without running pipeline).

    Returns:
        JSON object containing:
        - executive_summary: List of executive bullet points
        - themes: List of themes with mention counts (derived from articles)
        - articles: List of articles with metadata
        - run_id: The run ID
        - last_updated: Timestamp of last update
    """
    try:
        print("\n📊 Fetching most recent run data...")
        recent_run = get_most_recent_run()

        if not recent_run:
            return JSONResponse(content={
                "executive_summary": [],
                "themes": [],
                "articles": [],
                "run_id": None,
                "last_updated": datetime.now().isoformat()
            })

        run_fields = recent_run['fields']
        run_id_from_db = run_fields.get('Run ID', '')

        # Get executive summary from Runs table
        executive_summary_text = run_fields.get('Executive Summary', '')
        executive_summary = []
        if executive_summary_text:
            for line in executive_summary_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove numbering
                    line = line.lstrip('0123456789.-) ')
                    if line:
                        executive_summary.append(line)

        # Get articles from this run
        print(f"📰 Fetching articles from run: {run_id_from_db}...")
        articles = get_articles_by_run(run_id_from_db)

        if not articles:
            return JSONResponse(content={
                "executive_summary": executive_summary,
                "themes": [],
                "articles": [],
                "run_id": run_id_from_db,
                "last_updated": run_fields.get('Run Date', datetime.now().isoformat())
            })

        # Derive themes from articles using LLM
        print("🎯 Deriving themes from articles...")
        themes = derive_themes_from_articles(articles)

        # Count mentions for each theme
        print("🔍 Counting theme mentions...")
        theme_signals = []
        for theme in themes:
            count = count_theme_mentions(theme, articles)
            theme_signals.append({
                "theme": theme,
                "mentions": count
            })

        # Sort by mention count descending
        theme_signals.sort(key=lambda x: x['mentions'], reverse=True)

        # Format articles and assign themes
        print("📝 Formatting articles...")
        formatted_articles = []
        for article in articles:
            fields = article['fields']

            # Assign theme to article
            article_theme = assign_article_theme(fields.get('Summary', ''), themes)

            formatted_articles.append({
                "id": article['id'],
                "title": fields.get('Title', ''),
                "source": fields.get('Source', ''),
                "date": fields.get('Date', ''),
                "url": fields.get('URL', ''),
                "summary": fields.get('Summary', ''),
                "theme": article_theme
            })

        # Sort articles by date descending
        formatted_articles.sort(key=lambda x: x.get('date', ''), reverse=True)

        print("✅ Dashboard data ready!\n")

        return JSONResponse(content={
            "executive_summary": executive_summary,
            "themes": theme_signals,
            "articles": formatted_articles,
            "run_id": run_id_from_db,
            "last_updated": run_fields.get('Run Date', datetime.now().isoformat())
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching dashboard data: {str(e)}"
        )


@app.post("/dashboard/refresh")
def refresh_dashboard():
    """
    Run pipeline to fetch new articles and get dashboard data.

    Returns:
        JSON object containing:
        - executive_summary: List of executive bullet points
        - themes: List of themes with mention counts (derived from articles)
        - articles: List of articles with metadata
        - run_id: The run ID
        - last_updated: Timestamp of last update
    """
    try:
        # Step 1: Run the news pipeline to fetch new articles
        print("\n🚀 Running news intelligence pipeline...")
        run_id = run_news_pipeline(num_articles=20, verbose=False)
        print(f"✓ Pipeline completed: {run_id}")

        # Step 2: Get the most recent run data
        print("\n📊 Fetching most recent run data...")
        recent_run = get_most_recent_run()

        if not recent_run:
            return JSONResponse(content={
                "executive_summary": [],
                "themes": [],
                "articles": [],
                "run_id": None,
                "last_updated": datetime.now().isoformat()
            })

        run_fields = recent_run['fields']
        run_id_from_db = run_fields.get('Run ID', '')

        # Get executive summary from Runs table
        executive_summary_text = run_fields.get('Executive Summary', '')
        executive_summary = []
        if executive_summary_text:
            for line in executive_summary_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove numbering
                    line = line.lstrip('0123456789.-) ')
                    if line:
                        executive_summary.append(line)

        # Step 3: Get articles from this run
        print(f"📰 Fetching articles from run: {run_id_from_db}...")
        articles = get_articles_by_run(run_id_from_db)

        if not articles:
            return JSONResponse(content={
                "executive_summary": executive_summary,
                "themes": [],
                "articles": [],
                "run_id": run_id_from_db,
                "last_updated": run_fields.get('Run Date', datetime.now().isoformat())
            })

        # Step 4: Derive themes from articles using LLM
        print("🎯 Deriving themes from articles...")
        themes = derive_themes_from_articles(articles)

        # Step 5: Count mentions for each theme
        print("🔍 Counting theme mentions...")
        theme_signals = []
        for theme in themes:
            count = count_theme_mentions(theme, articles)
            theme_signals.append({
                "theme": theme,
                "mentions": count
            })

        # Sort by mention count descending
        theme_signals.sort(key=lambda x: x['mentions'], reverse=True)

        # Step 6: Update Runs table with theme counts
        print("💾 Updating Runs table with theme counts...")
        update_run_themes(run_id_from_db, theme_signals)

        # Step 7: Format articles and assign themes
        print("📝 Formatting articles and updating themes...")
        formatted_articles = []
        for article in articles:
            fields = article['fields']

            # Assign theme to article
            article_theme = assign_article_theme(fields.get('Summary', ''), themes)

            # Update article's Theme field in Airtable
            update_article_theme(article['id'], article_theme)

            formatted_articles.append({
                "id": article['id'],
                "title": fields.get('Title', ''),
                "source": fields.get('Source', ''),
                "date": fields.get('Date', ''),
                "url": fields.get('URL', ''),
                "summary": fields.get('Summary', ''),
                "theme": article_theme
            })

        # Sort articles by date descending
        formatted_articles.sort(key=lambda x: x.get('date', ''), reverse=True)

        print("✅ Dashboard data ready and Airtable updated!\n")

        return JSONResponse(content={
            "executive_summary": executive_summary,
            "themes": theme_signals,
            "articles": formatted_articles,
            "run_id": run_id_from_db,
            "last_updated": run_fields.get('Run Date', datetime.now().isoformat())
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching dashboard data: {str(e)}"
        )


@app.put("/dashboard/executive-summary")
def update_executive_summary_endpoint(data: Dict):
    """
    Update the executive summary for a specific run.

    Request body:
        {
            "run_id": "run_20250313_123456",
            "executive_summary": ["bullet 1", "bullet 2", ...]
        }

    Returns:
        Success message or error
    """
    try:
        run_id = data.get("run_id")
        executive_summary = data.get("executive_summary", [])

        if not run_id:
            raise HTTPException(status_code=400, detail="run_id is required")

        if not isinstance(executive_summary, list):
            raise HTTPException(status_code=400, detail="executive_summary must be a list")

        # Update the executive summary in Airtable
        updated = update_executive_summary(run_id, executive_summary)

        if not updated:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        return JSONResponse(content={
            "success": True,
            "message": "Executive summary updated successfully",
            "run_id": run_id
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating executive summary: {str(e)}"
        )


def assign_article_theme(summary: str, themes: List[str]) -> str:
    """
    Assign the most relevant theme to an article.

    Args:
        summary: Article summary
        themes: List of available themes

    Returns:
        Theme string
    """
    if not summary or not themes:
        return ""

    themes_text = "\n".join([f"{i+1}. {theme}" for i, theme in enumerate(themes)])

    prompt = f"""Given this article summary, select the most relevant theme from the list. Return only the theme text, nothing else.

Summary: {summary[:300]}

Themes:
{themes_text}"""

    response = call_llm(prompt, max_tokens=50)

    # Match to closest theme
    for theme in themes:
        if theme.lower() in response.lower() or response.lower() in theme.lower():
            return theme

    # Default to first theme if no match
    return themes[0] if themes else ""


def generate_executive_summary(articles: List[Dict]) -> List[str]:
    """
    Generate 5 executive summary bullet points from articles.

    Args:
        articles: List of article dictionaries

    Returns:
        List of 5 summary bullet points
    """
    if not articles:
        return []

    # Create summaries text
    summaries_text = "\n\n".join([
        f"- {article.get('title', '')}: {article.get('summary', '')[:200]}"
        for article in articles[:15]  # Use top 15 articles
    ])

    prompt = f"""Based on these whale migration news articles, create 5 executive summary bullet points that highlight the most important insights and trends.

Each bullet should be a single sentence that captures a key finding or trend. Be specific and data-driven where possible.

Return only the 5 bullet points, one per line, without numbers or bullets.

Articles:
{summaries_text}"""

    response = call_llm(prompt, max_tokens=500)

    # Parse bullet points
    bullets = []
    for line in response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # Remove numbering, bullets, etc.
        line = line.lstrip('0123456789.-•*) ')
        if line:
            bullets.append(line)

    return bullets[:5]  # Ensure exactly 5 bullets


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
