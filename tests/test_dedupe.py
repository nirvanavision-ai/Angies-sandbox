"""Tests for URL normalization and deduplication."""

import pytest

from trendbot.models import (
    TutorialResult,
    content_fingerprint,
    extract_youtube_id,
    normalize_url,
)
from trendbot.ranking.scorer import deduplicate


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_lowercases_host(self):
        assert normalize_url("https://EXAMPLE.COM/Page") == "https://example.com/Page"

    def test_removes_utm_params(self):
        url = "https://example.com/page?utm_source=twitter&utm_medium=social&id=123"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_removes_fbclid(self):
        url = "https://example.com/page?fbclid=abc123&real=param"
        result = normalize_url(url)
        assert "fbclid" not in result
        assert "real=param" in result

    def test_collapses_double_slashes(self):
        assert normalize_url("https://example.com//path///to//page") == "https://example.com/path/to/page"

    def test_upgrades_http_to_https(self):
        assert normalize_url("http://example.com/page").startswith("https://")

    def test_youtube_canonical_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share"
        assert normalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_canonical_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert normalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_canonical_embed(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert normalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_canonical_shorts(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert normalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_canonical_mobile(self):
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert normalize_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_empty_string(self):
        assert normalize_url("") == ""

    def test_preserves_non_tracking_params(self):
        url = "https://example.com/search?q=hello&page=2"
        result = normalize_url(url)
        assert "q=hello" in result
        assert "page=2" in result


class TestExtractYoutubeId:
    def test_standard_url(self):
        assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_youtube_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_youtube_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_non_youtube(self):
        assert extract_youtube_id("https://example.com/watch?v=abc") is None

    def test_youtube_no_id(self):
        assert extract_youtube_id("https://www.youtube.com/") is None


class TestContentFingerprint:
    def test_same_input_same_fingerprint(self):
        fp1 = content_fingerprint("My Tutorial", "https://example.com/tutorial")
        fp2 = content_fingerprint("My Tutorial", "https://example.com/tutorial")
        assert fp1 == fp2

    def test_different_title_different_fingerprint(self):
        fp1 = content_fingerprint("Tutorial A", "https://example.com/tutorial")
        fp2 = content_fingerprint("Tutorial B", "https://example.com/tutorial")
        assert fp1 != fp2

    def test_case_insensitive_title(self):
        fp1 = content_fingerprint("MY TUTORIAL", "https://example.com/tutorial")
        fp2 = content_fingerprint("my tutorial", "https://example.com/tutorial")
        assert fp1 == fp2

    def test_normalized_url(self):
        fp1 = content_fingerprint("Tutorial", "https://example.com/page?utm_source=x")
        fp2 = content_fingerprint("Tutorial", "https://example.com/page")
        assert fp1 == fp2


class TestDeduplicate:
    def test_removes_exact_dupes(self):
        results = [
            TutorialResult(title="Tutorial A", url="https://example.com/a"),
            TutorialResult(title="Tutorial A", url="https://example.com/a"),
        ]
        deduped = deduplicate(results)
        assert len(deduped) == 1

    def test_keeps_different_tutorials(self):
        results = [
            TutorialResult(title="Tutorial A", url="https://example.com/a"),
            TutorialResult(title="Tutorial B", url="https://example.com/b"),
        ]
        deduped = deduplicate(results)
        assert len(deduped) == 2

    def test_dedupes_youtube_variants(self):
        results = [
            TutorialResult(title="YT Tutorial", url="https://www.youtube.com/watch?v=abc123"),
            TutorialResult(title="YT Tutorial", url="https://youtu.be/abc123"),
        ]
        deduped = deduplicate(results)
        assert len(deduped) == 1

    def test_dedupes_with_utm_params(self):
        results = [
            TutorialResult(title="Tutorial", url="https://example.com/p"),
            TutorialResult(title="Tutorial", url="https://example.com/p?utm_source=twitter"),
        ]
        deduped = deduplicate(results)
        assert len(deduped) == 1

    def test_preserves_order(self):
        results = [
            TutorialResult(title="First", url="https://example.com/1"),
            TutorialResult(title="Second", url="https://example.com/2"),
            TutorialResult(title="First", url="https://example.com/1"),
        ]
        deduped = deduplicate(results)
        assert len(deduped) == 2
        assert deduped[0].title == "First"
        assert deduped[1].title == "Second"
