# Google Maps Scraper (Playwright)

This project scrapes Google Maps listings for a search term and exports:

- Company name
- Company email (best-effort from website/contact page)
- Website URL
- Rating
- Review count

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
python maps_scraper.py --query "Tokyo area in Seattle" --max-results 50 --headless --output seattle_tokyo.csv
```

## Notes

- Google Maps markup changes often; selectors may need occasional updates.
- Email extraction is best-effort and reads website HTML only.
- Respect Google Maps Terms of Service and applicable laws before scraping.
