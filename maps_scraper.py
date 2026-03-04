#!/usr/bin/env python3
"""Google Maps business scraper.

Usage:
  python maps_scraper.py --query "Tokyo area in Seattle" --max-results 50 --headless
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass, asdict
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class BusinessRecord:
    name: str
    email: str
    website: str
    rating: str
    review_count: str


def parse_rating_and_reviews(text: str) -> tuple[str, str]:
    """Extract rating + review count from a string near the listing title."""
    if not text:
        return "", ""

    rating_match = re.search(r"(\d\.\d)", text)
    review_match = re.search(r"(\d[\d,]*)\s+reviews?", text, flags=re.IGNORECASE)
    rating = rating_match.group(1) if rating_match else ""
    reviews = review_match.group(1).replace(",", "") if review_match else ""
    return rating, reviews


def extract_first_email_from_website(context_page: "Page", website_url: str, timeout_ms: int = 10_000) -> str:
    """Best-effort email extraction from a business website home/contact page."""
    if not website_url:
        return ""

    candidate_pages = [website_url]
    if website_url.endswith("/"):
        candidate_pages.append(f"{website_url}contact")
    else:
        candidate_pages.append(f"{website_url}/contact")

    for candidate in candidate_pages:
        try:
            response = context_page.request.get(candidate, timeout=timeout_ms)
            if not response.ok:
                continue
            body = response.text()
            match = EMAIL_REGEX.search(body)
            if match:
                return match.group(0)
        except Exception:
            continue
    return ""


def scroll_results_panel(page: "Page", iterations: int = 30, sleep_seconds: float = 1.0) -> None:
    """Scroll the left results panel to force lazy-loaded businesses to render."""
    panel = page.locator('div[role="feed"]')
    panel.wait_for(timeout=15_000)

    for _ in range(iterations):
        panel.evaluate("el => { el.scrollTop = el.scrollHeight; }")
        time.sleep(sleep_seconds)


def collect_listing_cards(page: "Page"):
    return page.locator('a[href*="/maps/place/"]')


def scrape_google_maps(query: str, max_results: int = 30, headless: bool = True) -> list[BusinessRecord]:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    records: list[BusinessRecord] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.google.com/maps", wait_until="domcontentloaded")

        search_box = page.locator('input#searchboxinput')
        search_box.fill(query)
        page.keyboard.press("Enter")

        try:
            scroll_results_panel(page)
        except PlaywrightTimeoutError:
            browser.close()
            return records

        cards = collect_listing_cards(page)
        total_cards = min(cards.count(), max_results)

        for i in range(total_cards):
            card = cards.nth(i)
            try:
                card.click(timeout=5_000)
                page.wait_for_timeout(1_500)
            except PlaywrightTimeoutError:
                continue

            name = page.locator("h1").first.inner_text(timeout=3_000) if page.locator("h1").count() else ""

            website = ""
            website_btn = page.locator('a[data-item-id="authority"]')
            if website_btn.count():
                website = website_btn.first.get_attribute("href") or ""

            rating_text = ""
            rating_el = page.locator('div[role="img"][aria-label*="stars"]').first
            if rating_el.count():
                rating_text = rating_el.get_attribute("aria-label") or ""

            rating, reviews = parse_rating_and_reviews(rating_text)
            email = extract_first_email_from_website(page, website)

            records.append(
                BusinessRecord(
                    name=name.strip(),
                    email=email,
                    website=website,
                    rating=rating,
                    review_count=reviews,
                )
            )

        browser.close()

    return records


def write_csv(records: Iterable[BusinessRecord], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "website", "rating", "review_count"])
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape Google Maps business data.")
    parser.add_argument("--query", required=True, help="Search query, e.g. 'Tokyo area in Seattle'.")
    parser.add_argument("--max-results", type=int, default=30, help="Maximum listings to scrape.")
    parser.add_argument("--output", default="maps_results.csv", help="Output CSV path.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    records = scrape_google_maps(
        query=args.query,
        max_results=args.max_results,
        headless=args.headless,
    )
    write_csv(records, args.output)
    print(f"Saved {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
