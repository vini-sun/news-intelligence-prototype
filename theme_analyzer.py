"""
Identify recurring themes across articles.
"""

import json
import os
from openai import OpenAI
from anthropic import Anthropic


INPUT_FILE = "data/processed_articles.json"
OUTPUT_FILE = "data/news_output.json"
THEME_IDENTIFICATION_PROMPT = "Across the following article summaries about whale migration, identify 3 to 5 recurring themes. Return only a list of themes."


def load_processed_articles(filepath=INPUT_FILE):
    """
    Load processed articles from JSON file.

    Args:
        filepath: Path to input JSON file

    Returns:
        List of processed article dictionaries
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"Loaded {len(articles)} processed articles from {filepath}")
    return articles


def identify_themes_openai(summaries, api_key=None):
    """
    Identify themes using OpenAI API.

    Args:
        summaries: List of article summaries
        api_key: OpenAI API key (optional)

    Returns:
        List of theme strings
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    summaries_text = "\n\n".join([f"- {summary}" for summary in summaries])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes news articles and identifies themes."},
            {"role": "user", "content": f"{THEME_IDENTIFICATION_PROMPT}\n\nSummaries:\n{summaries_text}"}
        ],
        temperature=0.5,
        max_tokens=300
    )

    themes_text = response.choices[0].message.content.strip()
    themes = parse_themes(themes_text)

    return themes


def identify_themes_claude(summaries, api_key=None):
    """
    Identify themes using Claude API.

    Args:
        summaries: List of article summaries
        api_key: Anthropic API key (optional)

    Returns:
        List of theme strings
    """
    client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    summaries_text = "\n\n".join([f"- {summary}" for summary in summaries])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {"role": "user", "content": f"{THEME_IDENTIFICATION_PROMPT}\n\nSummaries:\n{summaries_text}"}
        ]
    )

    themes_text = response.content[0].text.strip()
    themes = parse_themes(themes_text)

    return themes


def parse_themes(themes_text):
    """
    Parse themes from LLM response text.

    Args:
        themes_text: Raw text response from LLM

    Returns:
        List of theme strings
    """
    lines = themes_text.strip().split('\n')
    themes = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common list markers
        line = line.lstrip('0123456789.-•*) ')

        if line:
            themes.append(line)

    return themes


def assign_theme_openai(summary, themes, api_key=None):
    """
    Assign the most relevant theme to an article using OpenAI.

    Args:
        summary: Article summary
        themes: List of available themes
        api_key: OpenAI API key (optional)

    Returns:
        Theme string
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    themes_text = "\n".join([f"{i+1}. {theme}" for i, theme in enumerate(themes)])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that categorizes articles by theme."},
            {"role": "user", "content": f"Given this article summary, select the most relevant theme from the list. Return only the theme text, nothing else.\n\nSummary: {summary}\n\nThemes:\n{themes_text}"}
        ],
        temperature=0.3,
        max_tokens=100
    )

    assigned_theme = response.choices[0].message.content.strip()

    # Match to closest theme
    for theme in themes:
        if theme.lower() in assigned_theme.lower() or assigned_theme.lower() in theme.lower():
            return theme

    # Default to first theme if no match
    return themes[0] if themes else "Uncategorized"


def assign_theme_claude(summary, themes, api_key=None):
    """
    Assign the most relevant theme to an article using Claude.

    Args:
        summary: Article summary
        themes: List of available themes
        api_key: Anthropic API key (optional)

    Returns:
        Theme string
    """
    client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    themes_text = "\n".join([f"{i+1}. {theme}" for i, theme in enumerate(themes)])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[
            {"role": "user", "content": f"Given this article summary, select the most relevant theme from the list. Return only the theme text, nothing else.\n\nSummary: {summary}\n\nThemes:\n{themes_text}"}
        ]
    )

    assigned_theme = response.content[0].text.strip()

    # Match to closest theme
    for theme in themes:
        if theme.lower() in assigned_theme.lower() or assigned_theme.lower() in theme.lower():
            return theme

    # Default to first theme if no match
    return themes[0] if themes else "Uncategorized"


def analyze_themes(articles, provider="openai", api_key=None):
    """
    Identify recurring themes across articles.

    Args:
        articles: List of processed article dictionaries
        provider: LLM provider ('openai' or 'claude')
        api_key: API key (optional)

    Returns:
        List of theme strings
    """
    print(f"\nAnalyzing themes using {provider.upper()}...\n")

    # Extract summaries
    summaries = [article['summary'] for article in articles if article.get('summary')]

    # Identify themes
    print("Identifying recurring themes...")
    if provider == "openai":
        themes = identify_themes_openai(summaries, api_key)
    elif provider == "claude":
        themes = identify_themes_claude(summaries, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'claude'")

    print(f"\nIdentified {len(themes)} themes:")
    for i, theme in enumerate(themes):
        print(f"  {i+1}. {theme}")

    print(f"\n✓ Successfully identified {len(themes)} themes")
    return themes


def save_results(result, filepath=OUTPUT_FILE):
    """
    Save theme analysis results to JSON file.

    Args:
        result: Dictionary containing themes and articles
        filepath: Path to output JSON file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Saved results to {filepath}")


def main():
    """
    Main function to load, analyze themes, and save results.
    """
    # Load processed articles
    articles = load_processed_articles()

    if not articles:
        print("No articles to analyze")
        return

    # Analyze themes
    provider = os.getenv("LLM_PROVIDER", "openai")
    result = analyze_themes(articles, provider=provider)

    # Save results
    save_results(result)


if __name__ == "__main__":
    main()
