from __future__ import annotations

from unittest.mock import patch

from ytc.cli import search, SearchResult


class TestSearchFunction:
    """Test suite for the search function with prioritized keywords."""

    def test_empty_keywords_returns_empty_list(self) -> None:
        """Empty keyword list should return empty list."""
        assert search([]) == []
        assert search(()) == []

    def test_single_keyword_search(self) -> None:
        """Single keyword should be searched directly."""
        mock_result = SearchResult(
            phrase="python",
            title="Python Tutorial",
            upload_date="20250101",
            url="https://youtube.com/watch?v=abc123",
        )
        with patch("ytc.cli._search_yt_dlp") as mock_search:
            mock_search.return_value = [mock_result]
            result = search(["python"])
            mock_search.assert_called_once_with("python")
            assert result == [mock_result]

    def test_multiple_keywords_searched_as_phrase(self) -> None:
        """Multiple keywords should be searched as a single phrase."""
        mock_result = SearchResult(
            phrase="python tutorial beginner",
            title="Python Tutorial for Beginners",
            upload_date="20250101",
            url="https://youtube.com/watch?v=abc123",
        )
        with patch("ytc.cli._search_yt_dlp") as mock_search:
            mock_search.return_value = [mock_result]
            result = search(["python", "tutorial", "beginner"])
            mock_search.assert_called_once_with("python tutorial beginner")
            assert result == [mock_result]

    def test_falls_back_when_no_results_full_phrase(self) -> None:
        """Should fall back when full phrase yields no results."""
        call_log: list[str] = []

        def track_calls(query: str) -> list[SearchResult]:
            call_log.append(query)
            if query == "python tutorial beginner":
                return []
            return [
                SearchResult(
                    phrase=query,
                    title=f"Video for {query}",
                    upload_date="20250101",
                    url=f"https://youtube.com/watch?v={query.replace(' ', '_')}",
                )
            ]

        with patch("ytc.cli._search_yt_dlp", side_effect=track_calls):
            with patch("ytc.cli.time.sleep"):
                result = search(["python", "tutorial", "beginner"])

        assert call_log == [
            "python tutorial beginner",
            "python tutorial",
        ]
        assert len(result) == 1
        assert result[0].phrase == "python tutorial"
        assert result[0].url == "https://youtube.com/watch?v=python_tutorial"

    def test_continues_falling_back_until_results(self) -> None:
        """Should continue falling back until results found."""
        call_log: list[str] = []

        def track_calls(query: str) -> list[SearchResult]:
            call_log.append(query)
            return []

        with patch("ytc.cli._search_yt_dlp", side_effect=track_calls):
            with patch("ytc.cli.time.sleep"):
                result = search(["python", "tutorial", "advanced", "tips"])

        assert call_log == [
            "python tutorial advanced tips",
            "python tutorial advanced",
            "python tutorial",
            "python",
        ]
        assert result == []

    def test_stops_at_first_keyword_no_results(self) -> None:
        """Should return empty when even first keyword has no results."""
        with patch("ytc.cli._search_yt_dlp", return_value=[]):
            with patch("ytc.cli.time.sleep"):
                result = search(["rare", "search", "terms"])
        assert result == []

    def test_returns_first_successful_result(self) -> None:
        """Should return immediately when results found during fallback."""
        call_log: list[str] = []

        def track_calls(query: str) -> list[SearchResult]:
            call_log.append(query)
            if query == "deep learning":
                return [
                    SearchResult(
                        phrase=query,
                        title="Deep Learning Tutorial",
                        upload_date="20250101",
                        url="https://youtube.com/watch?v=ml123",
                    )
                ]
            return []

        with patch("ytc.cli._search_yt_dlp", side_effect=track_calls):
            with patch("ytc.cli.time.sleep"):
                result = search(["deep", "learning", "machine", "learning"])

        assert call_log == [
            "deep learning machine learning",
            "deep learning machine",
            "deep learning",
        ]
        assert len(result) == 1
        assert result[0].url == "https://youtube.com/watch?v=ml123"

    def test_multiple_results_returned(self) -> None:
        """Should return all results found."""
        expected_results = [
            SearchResult(
                phrase="test video",
                title="Test Video 1",
                upload_date="20250101",
                url="https://youtube.com/watch?v=abc123",
            ),
            SearchResult(
                phrase="test video",
                title="Test Video 2",
                upload_date="20250102",
                url="https://youtube.com/watch?v=def456",
            ),
            SearchResult(
                phrase="test video",
                title="Test Video 3",
                upload_date="20250103",
                url="https://youtube.com/watch?v=ghi789",
            ),
        ]
        with patch("ytc.cli._search_yt_dlp", return_value=expected_results):
            result = search(["test", "video"])
        assert result == expected_results

    def test_sleep_called_between_fallbacks(self) -> None:
        """Should sleep 0.5 seconds between fallback searches."""
        with patch("ytc.cli._search_yt_dlp") as mock_search:
            mock_search.side_effect = [[], [], []]
            with patch("ytc.cli.time.sleep") as mock_sleep:
                search(["a", "b", "c"])
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_no_sleep_when_immediate_result(self) -> None:
        """Should not sleep when full phrase returns results."""
        mock_result = SearchResult(
            phrase="a b c",
            title="Test",
            upload_date="20250101",
            url="https://youtube.com/watch?v=abc",
        )
        with patch("ytc.cli._search_yt_dlp", return_value=[mock_result]):
            with patch("ytc.cli.time.sleep") as mock_sleep:
                search(["a", "b", "c"])
        mock_sleep.assert_not_called()

    def test_no_sleep_when_no_results_at_all(self) -> None:
        """Should not sleep when there are no results at all."""
        with patch("ytc.cli._search_yt_dlp", return_value=[]):
            with patch("ytc.cli.time.sleep") as mock_sleep:
                search(["single"])
        mock_sleep.assert_not_called()

    def test_two_keywords_fallback(self) -> None:
        """Test fallback with exactly two keywords."""
        call_log: list[str] = []

        def track_calls(query: str) -> list[SearchResult]:
            call_log.append(query)
            if query == "full phrase":
                return []
            return [
                SearchResult(
                    phrase=query,
                    title=f"Video for {query}",
                    upload_date="20250101",
                    url="https://youtube.com/watch?v=fallback",
                )
            ]

        with patch("ytc.cli._search_yt_dlp", side_effect=track_calls):
            with patch("ytc.cli.time.sleep"):
                result = search(["full", "phrase"])

        assert call_log == ["full phrase", "full"]
        assert len(result) == 1
        assert result[0].url == "https://youtube.com/watch?v=fallback"

    def test_three_keywords_all_combinations(self) -> None:
        """Test all combinations with three keywords."""
        call_log: list[str] = []

        def track_calls(query: str) -> list[SearchResult]:
            call_log.append(query)
            return []

        with patch("ytc.cli._search_yt_dlp", side_effect=track_calls):
            with patch("ytc.cli.time.sleep"):
                search(["one", "two", "three"])

        assert call_log == [
            "one two three",
            "one two",
            "one",
        ]

    def test_search_result_fields(self) -> None:
        """Test that SearchResult has correct fields."""
        result = SearchResult(
            phrase="test query",
            title="Test Video Title",
            upload_date="20251231",
            url="https://youtube.com/watch?v=abc123",
            channel="Test Channel",
            channel_id="UCtest123",
            like_count=12345,
        )
        assert result.like_count == 12345
        assert result.phrase == "test query"
        assert result.title == "Test Video Title"
        assert result.upload_date == "20251231"
        assert result.url == "https://youtube.com/watch?v=abc123"
        assert result.channel == "Test Channel"
        assert result.channel_id == "UCtest123"

    def test_like_count_none(self) -> None:
        """Ensure None like_count is allowed."""
        result = SearchResult(
            phrase="test query",
            title="Test Video Title",
            upload_date="20251231",
            url="https://youtube.com/watch?v=abc123",
            channel="Test Channel",
            channel_id="UCtest123",
            like_count=None,
        )
        assert result.like_count is None
        assert result.phrase == "test query"
        assert result.title == "Test Video Title"
        assert result.upload_date == "20251231"
        assert result.url == "https://youtube.com/watch?v=abc123"
        assert result.channel == "Test Channel"
        assert result.channel_id == "UCtest123"
