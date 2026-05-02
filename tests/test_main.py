import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from kaira_event_reminder.main import Event, build_slack_text, extract_google_meet_url, format_place, parse_datetime


class MainTest(unittest.TestCase):
    def test_build_slack_text(self) -> None:
        event = Event(
            title="KaiRA 論文読み会",
            place="オンライン",
            url="https://kaira-thesis-reading.connpass.com/event/123456/",
            started_at=datetime(2026, 5, 2, 19, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            meet_url="https://meet.google.com/abc-defg-hij",
        )

        self.assertEqual(
            build_slack_text(event),
            "\n".join(
                [
                    "<!channel> 本日開催です！",
                    "- イベント名: KaiRA 論文読み会",
                    "- 場所: オンライン",
                    "- connpass: https://kaira-thesis-reading.connpass.com/event/123456/",
                    "- Google Meet: https://meet.google.com/abc-defg-hij",
                ]
            ),
        )

    def test_format_place_combines_place_and_address(self) -> None:
        self.assertEqual(format_place({"place": "会場", "address": "東京都千代田区"}), "会場 (東京都千代田区)")

    def test_parse_datetime_converts_to_jst(self) -> None:
        parsed = parse_datetime("2026-05-02T10:00:00+00:00", ZoneInfo("Asia/Tokyo"))

        self.assertEqual(parsed.hour, 19)
        self.assertEqual(parsed.tzinfo, ZoneInfo("Asia/Tokyo"))

    def test_extract_google_meet_url_from_description_html(self) -> None:
        description = '<p>会場: <a href="https://meet.google.com/abc-defg-hij">Meet</a></p>'

        self.assertEqual(extract_google_meet_url(description), "https://meet.google.com/abc-defg-hij")

    def test_extract_google_meet_url_returns_none_when_missing(self) -> None:
        self.assertIsNone(extract_google_meet_url("<p>オンライン開催です</p>"))


if __name__ == "__main__":
    unittest.main()
