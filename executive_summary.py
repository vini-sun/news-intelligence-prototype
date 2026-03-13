"""
Generate executive summary from analyzed data.
"""

import json
import os
from openai import OpenAI
from anthropic import Anthropic


INPUT_FILE = "data/news_output.json"
OUTPUT_FILE = "data/news_output.json"
EXECUTIVE_SUMMARY_PROMPT = "Based on the following article summaries about whale migration, generate a concise 5 bullet executive summary highlighting the most important developments."


def load_news_data(filepath=INPUT_FILE):
    """
    Load news data from JSON file.

    Args:
        filepath: Path to input JSON file

    Returns:
        Dictionary containing themes and articles
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded data from {filepath}")
    print(f"  - {len(data.get('themes', []))} themes")
    print(f"  - {len(data.get('articles', []))} articles")
    return data


def generate_executive_summary_openai(summaries, api_key=None):
    """
    Generate executive summary using OpenAI API.

    Args:
        summaries: List of article summaries
        api_key: OpenAI API key (optional)

    Returns:
        List of 5 executive summary bullets
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    summaries_text = "\n\n".join([f"- {summary}" for summary in summaries])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates executive summaries for leadership."},
            {"role": "user", "content": f"{EXECUTIVE_SUMMARY_PROMPT}\n\nSummaries:\n{summaries_text}"}
        ],
        temperature=0.6,
        max_tokens=400
    )

    summary_text = response.choices[0].message.content.strip()
    bullets = parse_bullets(summary_text)

    return bullets


def generate_executive_summary_claude(summaries, api_key=None):
    """
    Generate executive summary using Claude API.

    Args:
        summaries: List of article summaries
        api_key: Anthropic API key (optional)

    Returns:
        List of 5 executive summary bullets
    """
    client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    summaries_text = "\n\n".join([f"- {summary}" for summary in summaries])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[
            {"role": "user", "content": f"{EXECUTIVE_SUMMARY_PROMPT}\n\nSummaries:\n{summaries_text}"}
        ]
    )

    summary_text = response.content[0].text.strip()
    bullets = parse_bullets(summary_text)

    return bullets


def parse_bullets(summary_text):
    """
    Parse bullet points from LLM response text.

    Args:
        summary_text: Raw text response from LLM

    Returns:
        List of bullet point strings (exactly 5)
    """
    lines = summary_text.strip().split('\n')
    bullets = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip markdown headers (lines starting with #)
        if line.startswith('#'):
            continue

        # Skip lines that look like section headers or notes
        if line.lower().startswith('note:') or line.lower().startswith('**note'):
            continue

        # Remove common list markers
        cleaned_line = line.lstrip('0123456789.-•*) ')

        # Only add non-empty lines
        if cleaned_line and len(cleaned_line) > 10:  # Ignore very short lines
            bullets.append(cleaned_line)

    # Ensure we have exactly 5 bullets
    if len(bullets) < 5:
        # Pad with empty strings if needed
        bullets.extend([''] * (5 - len(bullets)))
    elif len(bullets) > 5:
        # Truncate to 5 if we have more
        bullets = bullets[:5]

    return bullets


def generate_executive_summary(data, provider="openai", api_key=None):
    """
    Generate executive summary from article data.

    Args:
        data: Dictionary containing themes and articles
        provider: LLM provider ('openai' or 'claude')
        api_key: API key (optional)

    Returns:
        Updated data dictionary with executive summary
    """
    print(f"\nGenerating executive summary using {provider.upper()}...\n")

    # Extract summaries
    articles = data.get('articles', [])
    summaries = [article['summary'] for article in articles if article.get('summary')]

    if not summaries:
        print("No summaries found to generate executive summary")
        return data

    # Generate executive summary
    try:
        if provider == "openai":
            executive_summary = generate_executive_summary_openai(summaries, api_key)
        elif provider == "claude":
            executive_summary = generate_executive_summary_claude(summaries, api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'claude'")

        print("Executive Summary:")
        for i, bullet in enumerate(executive_summary):
            print(f"  {i+1}. {bullet}")

        # Update data structure
        data['executive_summary'] = executive_summary

        print(f"\n✓ Successfully generated executive summary with {len(executive_summary)} bullets")

    except Exception as e:
        print(f"✗ Failed to generate executive summary: {str(e)}")
        data['executive_summary'] = ["Failed to generate executive summary"] * 5

    return data


def save_news_data(data, filepath=OUTPUT_FILE):
    """
    Save news data with executive summary to JSON file.

    Args:
        data: Dictionary containing executive summary, themes, and articles
        filepath: Path to output JSON file
    """
    # Ensure proper order: executive_summary, themes, articles
    ordered_data = {
        "executive_summary": data.get('executive_summary', []),
        "themes": data.get('themes', []),
        "articles": data.get('articles', [])
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(ordered_data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved complete news intelligence data to {filepath}")


def main():
    """
    Main function to load data, generate executive summary, and save results.
    """
    # Load news data
    data = load_news_data()

    if not data.get('articles'):
        print("No articles found in data")
        return

    # Generate executive summary
    provider = os.getenv("LLM_PROVIDER", "openai")
    updated_data = generate_executive_summary(data, provider=provider)

    # Save results
    save_news_data(updated_data)


if __name__ == "__main__":
    main()
