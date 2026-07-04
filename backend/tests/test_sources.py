from __future__ import annotations

import pytest

from app.sources.base import SearchFilters
from app.sources.google_source import GoogleSource
from app.sources.mock_source import MockSource
from app.sources.registry import get_registry
from app.sources.reddit_source import RedditSource
from app.sources.stubs import InstagramSource, LinkedInSource
from app.sources.twitter_source import TwitterSource


def test_mock_source_filters_by_query():
    source = MockSource()
    all_posts = source.search("", SearchFilters(limit=100))
    assert len(all_posts) >= 30

    f1_posts = source.search("Abu Dhabi GP", SearchFilters(limit=100))
    assert 0 < len(f1_posts) < len(all_posts)
    for post in f1_posts:
        assert post.source_key == "mock"
        assert post.external_id and post.content


def test_registry_skips_unavailable_sources():
    registry = get_registry()
    runnable_keys = {a.key for a in registry.runnable(["mock", "reddit", "google", "manual_url"])}
    # mock and manual_url need no keys; reddit/google are skipped without creds
    assert "mock" in runnable_keys
    assert "manual_url" in runnable_keys
    assert "reddit" not in runnable_keys
    assert "google" not in runnable_keys


def test_disabled_by_default_sources_do_not_run():
    registry = get_registry()
    assert not registry.is_enabled("twitter")
    assert not registry.is_enabled("instagram")
    assert registry.runnable(["twitter", "instagram", "facebook", "linkedin"]) == []


def test_unavailable_adapters_report_missing_keys():
    assert RedditSource(client_id=None, client_secret=None).available() is False
    assert set(RedditSource().required_keys) == {"REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"}
    assert GoogleSource(api_key=None, cse_id=None).available() is False
    assert TwitterSource(bearer=None).available() is False


def test_stub_platforms_raise_not_implemented():
    for source_cls in (InstagramSource, LinkedInSource):
        source = source_cls()
        assert source.available() is False
        with pytest.raises(NotImplementedError):
            source.search("anything", SearchFilters())


def test_manual_url_skips_non_http():
    from app.sources.manual_url import ManualUrlSource

    source = ManualUrlSource()
    assert source._fetch_page("ftp://example.com/x") is None
    assert source._fetch_page("javascript:alert(1)") is None
