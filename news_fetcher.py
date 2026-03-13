"""
Fetch articles using NewsData.io and TheNewsAPI.com.
"""

import json
import os
import requests
from datetime import datetime, timedelta


OUTPUT_FILE = "data/articles.json"
SEARCH_QUERY = "whale migration"

# API endpoints
NEWSDATA_URL = "https://newsdata.io/api/1/news"
THENEWSAPI_URL = "https://api.thenewsapi.com/v1/news/all"


def fetch_from_newsdata(num_articles=10):
    """
    Fetch articles from NewsData.io.

    Args:
        num_articles: Number of articles to fetch (max 10 per request)

    Returns:
        List of article dictionaries
    """
    print(f"\nFetching from NewsData.io...")

    api_key = os.getenv("NEWS_DATA_KEY")
    if not api_key:
        print("  ⚠ NEWS_DATA_KEY not set, skipping NewsData.io")
        return []

    try:
        params = {
            'apikey': api_key,
            'q': SEARCH_QUERY,
            'language': 'en',
            'size': min(num_articles, 10)  # Max 10 per request on free tier
        }

        response = requests.get(NEWSDATA_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'success':
            print(f"  ✗ Error from NewsData.io: {data.get('message', 'Unknown error')}")
            return []

        articles_data = data.get('results', [])
        print(f"  ✓ Found {len(articles_data)} articles from NewsData.io")

        articles = []
        for article in articles_data:
            # Combine description and content
            description = article.get('description', '') or ''
            content = article.get('content', '') or ''
            full_text = f"{description}\n\n{content}".strip()

            article_data = {
                "title": article.get('title', 'Untitled'),
                "source": article.get('source_id', 'Unknown'),
                "date": article.get('pubDate', ''),
                "url": article.get('link', ''),
                "text": full_text
            }
            articles.append(article_data)

        return articles

    except Exception as e:
        print(f"  ✗ Error fetching from NewsData.io: {str(e)}")
        return []


def fetch_from_thenewsapi(num_articles=10):
    """
    Fetch articles from TheNewsAPI.com.

    Args:
        num_articles: Number of articles to fetch

    Returns:
        List of article dictionaries
    """
    print(f"\nFetching from TheNewsAPI.com...")

    api_key = os.getenv("THE_NEWS_API_KEY")
    if not api_key:
        print("  ⚠ THE_NEWS_API_KEY not set, skipping TheNewsAPI.com")
        return []

    try:
        params = {
            'api_token': api_key,
            'search': SEARCH_QUERY,
            'language': 'en',
            'limit': num_articles
        }

        response = requests.get(THENEWSAPI_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles_data = data.get('data', [])
        print(f"  ✓ Found {len(articles_data)} articles from TheNewsAPI.com")

        articles = []
        for article in articles_data:
            # Combine description and content
            description = article.get('description', '') or ''
            snippet = article.get('snippet', '') or ''
            full_text = f"{description}\n\n{snippet}".strip()

            article_data = {
                "title": article.get('title', 'Untitled'),
                "source": article.get('source', 'Unknown'),
                "date": article.get('published_at', ''),
                "url": article.get('url', ''),
                "text": full_text
            }
            articles.append(article_data)

        return articles

    except Exception as e:
        print(f"  ✗ Error fetching from TheNewsAPI.com: {str(e)}")
        return []


def deduplicate_articles(articles):
    """
    Remove duplicate articles based on title similarity.

    Args:
        articles: List of article dictionaries

    Returns:
        Deduplicated list of articles
    """
    seen_titles = set()
    unique_articles = []

    for article in articles:
        title_lower = article['title'].lower().strip()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)

    return unique_articles


def score_article_quality(article):
    """
    Score article quality based on date and content availability.

    Args:
        article: Article dictionary

    Returns:
        Quality score (higher is better)
    """
    score = 0

    # Check if date exists and is not empty
    if article.get('date') and len(article.get('date', '')) > 0:
        score += 10

    # Check text content length
    text_len = len(article.get('text', ''))
    if text_len > 200:
        score += 20
    elif text_len > 100:
        score += 10
    elif text_len > 50:
        score += 5

    # Check if title exists
    if article.get('title') and len(article.get('title', '')) > 10:
        score += 5

    # Check if source exists
    if article.get('source') and article.get('source') != 'Unknown':
        score += 5

    # Check if URL exists
    if article.get('url'):
        score += 5

    return score


def fetch_articles(num_articles=20):
    """
    Fetch articles from TheNewsAPI.com and select the best quality ones.

    Args:
        num_articles: Number of articles to return (default 20)

    Returns:
        List of article dictionaries
    """
    print(f"Fetching articles from TheNewsAPI.com...")

    # Fetch 25 articles to have a selection pool
    fetch_count = 25

    # Fetch from TheNewsAPI only
    all_articles = fetch_from_thenewsapi(fetch_count)

    if not all_articles:
        print("\n✗ No articles fetched")
        return []

    print(f"\n✓ Fetched {len(all_articles)} articles")

    # Score and sort articles by quality
    print("\nScoring articles by quality (date clarity and content)...")
    for article in all_articles:
        article['quality_score'] = score_article_quality(article)

    # Sort by quality score (highest first)
    sorted_articles = sorted(all_articles, key=lambda x: x['quality_score'], reverse=True)

    # Select top N articles
    selected_articles = sorted_articles[:num_articles]

    print(f"✓ Selected top {len(selected_articles)} articles based on quality")

    # Process and display
    articles = []
    for i, article in enumerate(selected_articles):
        print(f"\nProcessing article {i+1}/{len(selected_articles)}: {article['title'][:60]}...")
        print(f"  Quality score: {article['quality_score']}/45")

        if article['text'] and len(article['text']) > 50:
            print(f"  ✓ Successfully extracted {len(article['text'])} characters")
        else:
            print(f"  ⚠ Limited content available ({len(article['text'])} chars)")

        # Remove quality_score before adding to final list
        article_data = {k: v for k, v in article.items() if k != 'quality_score'}
        articles.append(article_data)

    print(f"\nSuccessfully processed {len(articles)} articles")
    return articles


def save_articles(articles, filepath=OUTPUT_FILE):
    """
    Save articles to JSON file.

    Args:
        articles: List of article dictionaries
        filepath: Path to output JSON file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(articles)} articles to {filepath}")


def main():
    """
    Main function to fetch and save articles.
    """
    articles = fetch_articles(num_articles=20)

    if articles:
        save_articles(articles)
    else:
        print("No articles to save")


if __name__ == "__main__":
    main()
