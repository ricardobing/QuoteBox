"""Tests para scraper, crawler e ingestor."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from app.scraper.crawler import CrawlResult, RawQuote, crawl_all_quotes, parse_quotes_from_html
from app.scraper.ingestor import (
    IngestResult,
    compute_text_hash,
    normalize_author,
    normalize_text_for_hash,
    upsert_quotes_idempotent,
)
from app.scraper.session import login_with_csrf


def test_normalize_text_for_hash_collapses_whitespace() -> None:
    raw = "  Hello   WORLD \n  from   QuoteBox  "
    normalized = normalize_text_for_hash(raw)
    assert normalized == "hello world from quotebox"


def test_compute_text_hash_is_deterministic() -> None:
    base = "consistency"
    assert compute_text_hash(base) == compute_text_hash(base)


def test_normalize_author() -> None:
    assert normalize_author("  Albert   Einstein ") == "albert einstein"


def test_login_sets_session_cookie() -> None:
    session = Mock()
    settings = Mock()
    settings.scrape_base_url = "https://quotes.toscrape.com"
    settings.scrape_username = "ArchytasUser"
    settings.scrape_password = "123"

    login_page_html = (
        '<html><form><input name="csrf_token" value="abc123token"/></form>'
        '<a href="/logout">Logout</a></html>'
    )
    auth_page_html = '<html><a href="/logout">Logout</a></html>'

    get_response = Mock()
    get_response.text = login_page_html
    get_response.raise_for_status = Mock()

    post_response = Mock()
    post_response.text = auth_page_html
    post_response.raise_for_status = Mock()

    session.get.return_value = get_response
    session.post.return_value = post_response

    login_with_csrf(session, settings)

    session.get.assert_called_once_with("https://quotes.toscrape.com/login", timeout=20)
    session.post.assert_called_once()
    call_args = session.post.call_args
    assert call_args[0][0] == "https://quotes.toscrape.com/login"
    assert call_args[1]["data"]["username"] == "ArchytasUser"
    assert call_args[1]["data"]["password"] == "123"
    assert call_args[1]["data"]["csrf_token"] == "abc123token"


def test_parse_quotes_from_html() -> None:
    html = """<div class="quote">
        <span class="text">"The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking."</span>
        <small class="author">Albert Einstein</small>
        <div class="tags">
            <a class="tag">change</a>
            <a class="tag">deep-thoughts</a>
            <a class="tag">thinking</a>
            <a class="tag">world</a>
        </div>
    </div>
    <div class="quote">
        <span class="text">"It is our choices, Harry, that show what we truly are, far more than our abilities."</span>
        <small class="author">J.K. Rowling</small>
        <div class="tags">
            <a class="tag">abilities</a>
            <a class="tag">choices</a>
        </div>
    </div>"""

    quotes = parse_quotes_from_html(html)
    assert len(quotes) == 2

    assert quotes[0].author == "Albert Einstein"
    assert "world as we have created it" in quotes[0].text.lower()
    assert "change" in quotes[0].tags
    assert "thinking" in quotes[0].tags

    assert quotes[1].author == "J.K. Rowling"
    assert "choices" in quotes[1].tags
    assert "abilities" in quotes[1].tags


def test_crawl_stops_at_last_page() -> None:
    session = Mock()
    settings = Mock()
    settings.scrape_base_url = "https://quotes.toscrape.com"

    page1_html = """<div class="quote">
        <span class="text">"Quote one"</span>
        <small class="author">Author One</small>
        <div class="tags"><a class="tag">love</a></div>
    </div>
    <ul class="pager"><li class="next"><a href="/page/2/">Next</a></li></ul>"""

    page2_html = """<div class="quote">
        <span class="text">"Quote two"</span>
        <small class="author">Author Two</small>
        <div class="tags"><a class="tag">life</a></div>
    </div>"""

    resp1 = Mock()
    resp1.text = page1_html
    resp1.raise_for_status = Mock()
    resp2 = Mock()
    resp2.text = page2_html
    resp2.raise_for_status = Mock()

    session.get.side_effect = [resp1, resp2]

    result = crawl_all_quotes(session, settings)

    assert result.pages_scraped == 2
    assert len(result.quotes) == 2
    assert result.quotes[0].text == "Quote one"
    assert result.quotes[1].text == "Quote two"
    assert session.get.call_count == 2


def test_upsert_idempotency_with_mock() -> None:
    supabase = Mock()
    table_mock = Mock()
    upsert_mock = Mock()
    upsert_mock.execute.return_value.data = [{"id": "fake"}]
    table_mock.upsert.return_value = upsert_mock
    supabase.table.return_value = table_mock

    quotes = [
        RawQuote(text="Quote A", author="Author A", tags=["love"]),
        RawQuote(text="Quote B", author="Author B", tags=["life"]),
    ]
    active_tags = {"love", "life"}

    result = upsert_quotes_idempotent(supabase, quotes, active_tags)
    assert result.quotes_seen == 2
    assert result.quotes_inserted == 2

    # Second run with empty data (all duplicates)
    upsert_mock.execute.return_value.data = []
    result2 = upsert_quotes_idempotent(supabase, quotes, active_tags)
    assert result2.quotes_inserted == 0
