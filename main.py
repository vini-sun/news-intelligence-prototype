"""
Main entry point for news intelligence prototype.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import pipeline modules
from news_fetcher import fetch_articles, save_articles
from summarizer import load_articles, process_articles, save_processed_articles
from theme_analyzer import load_processed_articles, analyze_themes, save_results
from executive_summary import load_news_data, generate_executive_summary, save_news_data
from airtable_client import insert_articles, insert_run


def print_header(message):
    """Print formatted header message."""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60)


def print_step(step_num, message):
    """Print formatted step message."""
    print(f"\n[Step {step_num}/5] {message}")
    print("-" * 60)


def verify_api_key(provider="openai"):
    """
    Verify that API key is set.

    Args:
        provider: LLM provider ('openai' or 'claude')

    Returns:
        bool: True if API key is set, False otherwise
    """
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
    elif provider == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    return True


def run_news_pipeline(num_articles=20, provider=None, verbose=True):
    """
    Run the complete news intelligence pipeline.

    Steps:
    1. Fetch latest RSS articles
    2. Extract article text
    3. Generate summaries
    4. Identify themes
    5. Generate executive summary
    6. Write results to Airtable

    Args:
        num_articles: Number of articles to fetch (default: 20)
        provider: LLM provider ('openai' or 'claude', defaults to env or 'openai')
        verbose: Print progress messages (default: True)

    Returns:
        str: run_id for this pipeline execution

    Raises:
        ValueError: If API keys are not set
        Exception: If pipeline fails
    """
    start_time = datetime.now()

    # Generate run_id for this pipeline execution
    run_id = f"run_{start_time.strftime('%Y%m%d_%H%M%S')}"

    # Get LLM provider
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if verbose:
        print_header("News Intelligence Prototype")
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Run ID: {run_id}")
        print(f"Using LLM provider: {provider.upper()}")

    # Verify API key is set
    verify_api_key(provider)

    # Step 1: Fetch articles
    if verbose:
        print_step(1, "Fetching articles...")

    articles = fetch_articles(num_articles=num_articles)

    if not articles:
        raise Exception("No articles fetched from RSS feed")

    save_articles(articles)

    if verbose:
        print(f"✓ Fetched and saved {len(articles)} articles")

    # Step 2: Summarize articles
    if verbose:
        print_step(2, "Summarizing articles...")

    articles_to_summarize = load_articles()
    processed_articles = process_articles(articles_to_summarize, provider=provider)

    if not processed_articles:
        raise Exception("No articles processed")

    save_processed_articles(processed_articles)

    if verbose:
        print(f"✓ Generated summaries for {len(processed_articles)} articles")

    # Step 3: Analyze themes
    if verbose:
        print_step(3, "Analyzing themes...")

    articles_for_themes = load_processed_articles()
    themes = analyze_themes(articles_for_themes, provider=provider)

    if not themes:
        raise Exception("Theme analysis failed")

    # Save themes and articles to output file
    theme_data = {
        "themes": themes,
        "articles": articles_for_themes
    }
    save_results(theme_data)

    if verbose:
        print(f"✓ Identified {len(themes)} themes")

    # Step 4: Sync to Airtable
    if verbose:
        print_step(4, "Syncing to Airtable...")

    # Prepare articles for Airtable with run_id (no individual themes)
    articles_for_airtable = []
    for article in articles_for_themes:
        airtable_article = {
            "title": article.get('title', ''),
            "source": article.get('source', ''),
            "date": article.get('date', ''),
            "url": article.get('url', ''),
            "summary": article.get('summary', ''),
            "run_id": run_id,
            "created_at": datetime.now().isoformat()
        }
        articles_for_airtable.append(airtable_article)

    # Insert into Airtable
    airtable_records = insert_articles(articles_for_airtable)

    if verbose:
        print(f"✓ Synced {len(airtable_records)} articles to Airtable")

    # Step 5: Generate executive summary
    if verbose:
        print_step(5, "Generating executive summary...")

    news_data = load_news_data()
    final_data = generate_executive_summary(news_data, provider=provider)

    save_news_data(final_data)

    if verbose:
        print("✓ Generated 5-bullet executive summary")

    # Insert run metadata into Runs table
    if verbose:
        print("\nSyncing run metadata to Airtable...")

    run_data = {
        "run_id": run_id,
        "run_date": start_time.isoformat(),
        "executive_summary": final_data.get('executive_summary', []),
        "themes": final_data.get('themes', [])
    }
    run_record = insert_run(run_data)

    # Success summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if verbose:
        print_header("Pipeline Complete!")
        print(f"\nFinal output saved to: data/news_output.json")
        print(f"Airtable sync complete:")
        print(f"  - Articles: {len(airtable_records)} records")
        print(f"  - Run metadata: 1 record")
        print(f"\nPipeline Statistics:")
        print(f"  - Run ID: {run_id}")
        print(f"  - Articles fetched: {len(articles)}")
        print(f"  - Summaries generated: {len(processed_articles)}")
        print(f"  - Themes identified: {len(themes)}")
        print(f"  - Articles synced to Airtable: {len(airtable_records)}")
        print(f"  - Executive bullets: {len(final_data.get('executive_summary', []))}")
        print(f"  - Total runtime: {duration:.2f} seconds")
        print(f"\nCompleted at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    return run_id


def main():
    """
    Main entry point when script is run directly.
    """
    try:
        run_id = run_news_pipeline()
        print(f"\n✓ Pipeline completed successfully: {run_id}")

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nERROR: Pipeline failed with exception:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
