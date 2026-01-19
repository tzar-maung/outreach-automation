"""
Task loader for loading targets from CSV files.
"""
import csv
from pathlib import Path


def load_targets(path: Path):
    """
    Load target URLs from a CSV file.
    
    Expected format:
        url
        https://instagram.com/user1
        https://instagram.com/user2
    
    Args:
        path: Path to the CSV file
    
    Returns:
        List of target URLs
    """
    targets = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if "url" not in reader.fieldnames:
            raise ValueError("targets.csv must contain a 'url' column")

        for row in reader:
            if row["url"].strip():
                targets.append(row["url"].strip())

    return targets


def save_results(path: Path, results: list):
    """
    Save results to a CSV file.
    
    Args:
        path: Path to output file
        results: List of result dictionaries
    """
    if not results:
        return
    
    fieldnames = results[0].keys()
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
