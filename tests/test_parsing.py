from maps_scraper import parse_rating_and_reviews


def test_parse_rating_and_reviews_full_text():
    rating, reviews = parse_rating_and_reviews("4.7 stars 1,284 reviews")
    assert rating == "4.7"
    assert reviews == "1284"


def test_parse_rating_and_reviews_missing_reviews():
    rating, reviews = parse_rating_and_reviews("Rated 4.2 stars")
    assert rating == "4.2"
    assert reviews == ""


def test_parse_rating_and_reviews_empty():
    rating, reviews = parse_rating_and_reviews("")
    assert rating == ""
    assert reviews == ""
