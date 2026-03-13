"""
Generate summaries of articles using LLM.
"""

import json
import os
from openai import OpenAI
from anthropic import Anthropic


INPUT_FILE = "data/articles.json"
OUTPUT_FILE = "data/processed_articles.json"
SUMMARY_PROMPT = "Summarize this article in 2 concise sentences focusing on the key development related to whale migration."


def load_articles(filepath=INPUT_FILE):
    """
    Load articles from JSON file.

    Args:
        filepath: Path to input JSON file

    Returns:
        List of article dictionaries
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"Loaded {len(articles)} articles from {filepath}")
    return articles


def summarize_with_openai(article_text, api_key=None):
    """
    Generate summary using OpenAI API.

    Args:
        article_text: The article text to summarize
        api_key: OpenAI API key (optional, defaults to env variable)

    Returns:
        Summary string
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news articles."},
            {"role": "user", "content": f"{SUMMARY_PROMPT}\n\nArticle:\n{article_text}"}
        ],
        temperature=0.7,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()


def summarize_with_claude(article_text, api_key=None):
    """
    Generate summary using Claude API.

    Args:
        article_text: The article text to summarize
        api_key: Anthropic API key (optional, defaults to env variable)

    Returns:
        Summary string
    """
    client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[
            {"role": "user", "content": f"{SUMMARY_PROMPT}\n\nArticle:\n{article_text}"}
        ]
    )

    return response.content[0].text.strip()


def summarize_article(article_text, provider="openai", api_key=None):
    """
    Generate summary for a single article using specified LLM provider.

    Args:
        article_text: The article text to summarize
        provider: LLM provider ('openai' or 'claude')
        api_key: API key (optional)

    Returns:
        Summary string
    """
    if provider == "openai":
        return summarize_with_openai(article_text, api_key)
    elif provider == "claude":
        return summarize_with_claude(article_text, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'claude'")


def process_articles(articles, provider="openai", api_key=None):
    """
    Process all articles and generate summaries.

    Args:
        articles: List of article dictionaries
        provider: LLM provider to use
        api_key: API key (optional)

    Returns:
        List of processed article dictionaries
    """
    print(f"\nGenerating summaries using {provider.upper()}...\n")

    processed_articles = []

    for i, article in enumerate(articles):
        print(f"Processing {i+1}/{len(articles)}: {article['title'][:60]}...")

        # Skip summarization if article text is empty or too short
        if not article.get('text') or len(article.get('text', '')) < 100:
            print(f"  ⚠ No article text available, using title as summary")
            processed_article = {
                "title": article['title'],
                "source": article['source'],
                "date": article.get('date', ''),
                "url": article['url'],
                "summary": f"Article about {article['title']}"
            }
            processed_articles.append(processed_article)
            continue

        try:
            summary = summarize_article(article['text'], provider=provider, api_key=api_key)

            processed_article = {
                "title": article['title'],
                "source": article['source'],
                "date": article.get('date', ''),
                "url": article['url'],
                "summary": summary
            }

            processed_articles.append(processed_article)
            print(f"  ✓ Summary generated ({len(summary)} chars)")

        except Exception as e:
            print(f"  ✗ Failed to generate summary: {str(e)}")
            processed_article = {
                "title": article['title'],
                "source": article['source'],
                "date": article.get('date', ''),
                "url": article['url'],
                "summary": f"Article about {article['title']}"
            }
            processed_articles.append(processed_article)

    print(f"\nSuccessfully processed {len(processed_articles)} articles")
    return processed_articles


def save_processed_articles(articles, filepath=OUTPUT_FILE):
    """
    Save processed articles to JSON file.

    Args:
        articles: List of processed article dictionaries
        filepath: Path to output JSON file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(articles)} processed articles to {filepath}")


def main():
    """
    Main function to load, summarize, and save articles.
    """
    # Load articles
    articles = load_articles()

    if not articles:
        print("No articles to process")
        return

    # Process articles (defaults to OpenAI, can change to 'claude')
    provider = os.getenv("LLM_PROVIDER", "openai")
    processed_articles = process_articles(articles, provider=provider)

    # Save results
    save_processed_articles(processed_articles)


if __name__ == "__main__":
    main()
