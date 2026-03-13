"""
Airtable client for storing news intelligence data.
"""

import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
from pyairtable import Table

# Load environment variables
load_dotenv()

# Airtable configuration
AIRTABLE_ACCESS_TOKEN = os.getenv("AIRTABLE_ACCESS_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appw2nAjTdqYtg0nT")
AIRTABLE_TABLE_NAME = "Articles"
AIRTABLE_RUNS_TABLE_NAME = "Runs"


def get_table():
    """
    Get Airtable Articles table instance.

    Returns:
        pyairtable.Table: Airtable table object
    """
    table = Table(AIRTABLE_ACCESS_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    return table


def get_runs_table():
    """
    Get Airtable Runs table instance.

    Returns:
        pyairtable.Table: Airtable runs table object
    """
    table = Table(AIRTABLE_ACCESS_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_RUNS_TABLE_NAME)
    return table


def convert_date_to_iso(date_string):
    """
    Convert date string to ISO format (YYYY-MM-DD) for Airtable.

    Args:
        date_string: Date in various formats (ISO, RFC, etc.)

    Returns:
        Date in ISO format (YYYY-MM-DD) or empty string if parsing fails
    """
    if not date_string:
        return ""

    try:
        # Try parsing ISO format first (e.g., "2025-11-20T06:29:59.000000Z")
        if 'T' in date_string:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")

        # Try parsing RFC date format (e.g., "Mon, 09 Mar 2026 07:00:00 GMT")
        dt = parsedate_to_datetime(date_string)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # If all parsing fails, return empty string
        return ""


def sanitize_theme(theme):
    """
    Sanitize theme value for Airtable select field.

    Args:
        theme: Theme string

    Returns:
        Empty string if theme looks like an error message, otherwise cleaned theme
    """
    if not theme:
        return ""

    # If theme contains error indicators, return empty string
    error_indicators = [
        "no themes", "error", "not able", "unable", "didn't come through",
        "please paste", "here is a list", "limitations", "note:", "several summaries",
        "paywalled", "incomplete content", "off-topic", "cryptocurrency", "not suitable"
    ]
    theme_lower = theme.lower()

    for indicator in error_indicators:
        if indicator in theme_lower:
            return ""

    # Clean up markdown formatting and special characters
    clean_theme = theme.replace("**", "").replace("*", "").strip()

    # Remove parenthetical details to keep it concise
    if "(" in clean_theme:
        clean_theme = clean_theme.split("(")[0].strip()

    # If theme is too long (likely an error message), return empty
    if len(clean_theme) > 100:
        return ""

    # If theme is too short or empty after cleaning, return empty
    if len(clean_theme) < 3:
        return ""

    return clean_theme


def insert_article(article_data):
    """
    Insert a single article into Airtable.

    Args:
        article_data: Dictionary containing article fields:
            - title: Article title
            - source: News source
            - date: Publication date
            - url: Article URL
            - summary: Article summary
            - theme: Assigned theme
            - run_id: Pipeline run identifier
            - created_at: Timestamp (optional, defaults to now)

    Returns:
        dict: Created Airtable record
    """
    table = get_table()

    # Prepare record with proper field names
    record = {
        "Title": article_data.get("title", ""),
        "Source": article_data.get("source", ""),
        "URL": article_data.get("url", ""),
        "Summary": article_data.get("summary", ""),
        "Run ID": article_data.get("run_id", "")
    }

    # Only add Date if it has a valid value
    date_iso = convert_date_to_iso(article_data.get("date", ""))
    if date_iso:
        record["Date"] = date_iso

    # Only add Theme if it has a valid value
    theme = sanitize_theme(article_data.get("theme", ""))
    if theme:
        record["Theme"] = theme

    created_record = table.create(record)
    print(f"  ✓ Inserted: {record['Title'][:60]}...")

    return created_record


def insert_articles(list_of_articles):
    """
    Insert multiple articles into Airtable in batch.

    Args:
        list_of_articles: List of article dictionaries

    Returns:
        list: List of created Airtable records
    """
    table = get_table()

    print(f"\nInserting {len(list_of_articles)} articles into Airtable...")

    # Prepare records for batch creation
    records = []
    for article in list_of_articles:
        record = {
            "Title": article.get("title", ""),
            "Source": article.get("source", ""),
            "URL": article.get("url", ""),
            "Summary": article.get("summary", ""),
            "Run ID": article.get("run_id", "")
        }

        # Only add Date if it has a valid value
        date_iso = convert_date_to_iso(article.get("date", ""))
        if date_iso:
            record["Date"] = date_iso

        # Only add Theme if it has a valid value
        theme = sanitize_theme(article.get("theme", ""))
        if theme:
            record["Theme"] = theme

        records.append(record)

    # Insert in batches of 10 (Airtable API limit)
    created_records = []
    for i in range(0, len(records), 10):
        batch = records[i:i+10]
        batch_created = table.batch_create(batch)
        created_records.extend(batch_created)
        print(f"  ✓ Inserted batch {i//10 + 1}: {len(batch_created)} records")

    print(f"✓ Successfully inserted {len(created_records)} articles into Airtable")

    return created_records


def clear_articles_for_run(run_id):
    """
    Clear all articles for a specific run_id.

    Args:
        run_id: Pipeline run identifier

    Returns:
        int: Number of records deleted
    """
    table = get_table()

    print(f"\nClearing articles for run_id: {run_id}...")

    # Get all records with matching run_id
    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    if not records:
        print(f"  No records found for run_id: {run_id}")
        return 0

    # Delete records in batches of 10
    record_ids = [record['id'] for record in records]
    deleted_count = 0

    for i in range(0, len(record_ids), 10):
        batch = record_ids[i:i+10]
        table.batch_delete(batch)
        deleted_count += len(batch)

    print(f"✓ Deleted {deleted_count} records for run_id: {run_id}")

    return deleted_count


def get_articles_by_run(run_id):
    """
    Retrieve all articles for a specific run_id.

    Args:
        run_id: Pipeline run identifier

    Returns:
        list: List of article records
    """
    table = get_table()

    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    return records


def get_all_articles():
    """
    Retrieve all articles from Airtable.

    Returns:
        list: List of all article records
    """
    table = get_table()
    records = table.all()

    return records


# ============================================================================
# Runs Table Functions
# ============================================================================

def insert_run(run_data):
    """
    Insert a run record into the Runs table.

    Args:
        run_data: Dictionary containing run fields:
            - run_id: Pipeline run identifier
            - run_date: Date/time of the run
            - executive_summary: List of executive summary bullets
            - themes: List of identified themes

    Returns:
        dict: Created Airtable record
    """
    table = get_runs_table()

    # Format executive summary as numbered list
    executive_summary_list = run_data.get("executive_summary", [])
    executive_summary_text = "\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(executive_summary_list)])

    # Format themes as comma-separated list
    themes_list = run_data.get("themes", [])
    themes_text = ", ".join(themes_list)

    # Prepare record with proper field names
    record = {
        "Run ID": run_data.get("run_id", ""),
        "Run Date": run_data.get("run_date", datetime.now().isoformat()),
        "Executive Summary": executive_summary_text,
        "Themes": themes_text
    }

    created_record = table.create(record)
    print(f"\n✓ Inserted run record: {record['Run ID']}")

    return created_record


def get_run_by_id(run_id):
    """
    Retrieve a specific run by run_id.

    Args:
        run_id: Pipeline run identifier

    Returns:
        dict: Run record or None if not found
    """
    table = get_runs_table()

    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    return records[0] if records else None


def get_all_runs():
    """
    Retrieve all runs from Airtable.

    Returns:
        list: List of all run records
    """
    table = get_runs_table()
    records = table.all()

    return records


def get_most_recent_run():
    """
    Get the most recent run from Airtable.

    Returns:
        dict: Most recent run record or None if no runs exist
    """
    table = get_runs_table()

    # Sort by Run Date descending to get most recent (use '-' prefix for descending)
    records = table.all(sort=['-Run Date'])

    return records[0] if records else None


def delete_run(run_id):
    """
    Delete a run record by run_id.

    Args:
        run_id: Pipeline run identifier

    Returns:
        bool: True if deleted, False if not found
    """
    table = get_runs_table()

    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    if records:
        table.delete(records[0]['id'])
        print(f"✓ Deleted run record: {run_id}")
        return True

    print(f"Run record not found: {run_id}")
    return False


def update_run_themes(run_id, themes_with_counts):
    """
    Update the Themes field in a run record with themes and their mention counts.

    Args:
        run_id: Pipeline run identifier
        themes_with_counts: List of dicts with 'theme' and 'mentions' keys

    Returns:
        dict: Updated run record or None if not found
    """
    table = get_runs_table()

    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    if not records:
        print(f"Run record not found: {run_id}")
        return None

    # Format themes as "Theme1: 5, Theme2: 3, Theme3: 2"
    themes_text = ", ".join([f"{t['theme']}: {t['mentions']}" for t in themes_with_counts])

    # Update the record
    updated = table.update(records[0]['id'], {"Themes": themes_text})
    print(f"✓ Updated themes for run: {run_id}")

    return updated


def update_article_theme(article_id, theme):
    """
    Update the Theme field for an article.

    Args:
        article_id: Airtable record ID
        theme: Theme string to assign

    Returns:
        dict: Updated article record or None if update fails
    """
    table = get_table()
    try:
        updated = table.update(article_id, {"Theme": theme})
        return updated
    except Exception as e:
        # If theme doesn't exist in Airtable select options, skip silently
        if "INVALID_MULTIPLE_CHOICE_OPTIONS" in str(e):
            print(f"  ⚠ Skipping theme update for article {article_id}: theme '{theme}' not in Airtable options")
            return None
        else:
            # Re-raise other errors
            raise


def update_executive_summary(run_id, executive_summary_list):
    """
    Update the Executive Summary field for a run.

    Args:
        run_id: Pipeline run identifier
        executive_summary_list: List of executive summary bullet points

    Returns:
        dict: Updated run record or None if not found
    """
    table = get_runs_table()

    formula = f"{{Run ID}} = '{run_id}'"
    records = table.all(formula=formula)

    if not records:
        print(f"Run record not found: {run_id}")
        return None

    # Format executive summary as numbered list
    executive_summary_text = "\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(executive_summary_list)])

    # Update the record
    updated = table.update(records[0]['id'], {"Executive Summary": executive_summary_text})
    print(f"✓ Updated executive summary for run: {run_id}")

    return updated
