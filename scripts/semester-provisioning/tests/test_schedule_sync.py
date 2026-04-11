# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
import pytest
from api.utils.schedule_sync import ScheduleSyncEngine, ScheduleSyncError


@pytest.fixture
def schedule_sync_engine():
    """Create ScheduleSyncEngine instance for testing."""
    return ScheduleSyncEngine()


@pytest.fixture
def mock_schedule_event():
    """Mock schedule event data."""
    return {
        "uid": "evt-001",
        "title": "Einführung in die Informatik",
        "start": "20261015T090000Z",
        "end": "20261015T110000Z",
        "room": "H1.1",
        "recurrence": "FREQ=WEEKLY;BYDAY=MO,FR",
    }


@pytest.mark.asyncio
class TestScheduleSyncEngineMockMode:
    """Test ScheduleSyncEngine in mock mode."""

    async def test_initialization(self, schedule_sync_engine):
        """Test engine initialization."""
        assert schedule_sync_engine.hisinone_client is not None

    async def test_is_configured(self, schedule_sync_engine):
        """Test CalDAV configuration check."""
        # Should return False when CalDAV credentials are not set
        assert not schedule_sync_engine._is_configured()

    async def test_get_schedule_mock_mode(self, schedule_sync_engine):
        """Test get_schedule returns mock data."""
        async with schedule_sync_engine:
            schedule = await schedule_sync_engine.get_schedule("student-001", "2026ws")

            # Should return mock data
            assert isinstance(schedule, list)
            assert len(schedule) >= 5

            # Check structure of first event
            event = schedule[0]
            assert "uid" in event
            assert "title" in event
            assert "start" in event
            assert "end" in event

    async def test_sync_schedule_to_calendars_skipped(self, schedule_sync_engine):
        """Test sync_schedule_to_calendars skips when CalDAV not configured."""
        async with schedule_sync_engine:
            result = await schedule_sync_engine.sync_schedule_to_calendars(
                "student-001", "2026ws"
            )

            assert result["status"] == "skipped"
            assert result["reason"] == "CalDAV not configured"
            assert result["created"] == 0
            assert result["updated"] == 0

    def test_generate_ics_basic(self, schedule_sync_engine, mock_schedule_event):
        """Test generate_ics produces valid ICS format."""
        ics_content = schedule_sync_engine.generate_ics(mock_schedule_event)

        # Check ICS structure
        assert "BEGIN:VCALENDAR" in ics_content
        assert "VERSION:2.0" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "END:VCALENDAR" in ics_content

        # Check event properties
        assert f"UID:{mock_schedule_event['uid']}" in ics_content
        assert f"SUMMARY:{mock_schedule_event['title']}" in ics_content
        assert f"DTSTART:{mock_schedule_event['start']}" in ics_content
        assert f"DTEND:{mock_schedule_event['end']}" in ics_content
        assert f"LOCATION:{mock_schedule_event['room']}" in ics_content
        assert f"RRULE:{mock_schedule_event['recurrence']}" in ics_content

    def test_generate_ics_datetime_conversion(self, schedule_sync_engine):
        """Test generate_ics converts datetime objects to ICS format."""
        from datetime import datetime

        event = {
            "uid": "evt-datetime",
            "title": "Test Event",
            "start": datetime(2026, 10, 15, 9, 0),
            "end": datetime(2026, 10, 15, 11, 0),
            "room": "H1.1",
            "recurrence": "",
        }

        ics_content = schedule_sync_engine.generate_ics(event)

        # Check datetime was converted to ICS format
        assert "DTSTART:20261015T090000Z" in ics_content
        assert "DTEND:20261015T110000Z" in ics_content

    def test_generate_ics_without_recurrence(self, schedule_sync_engine):
        """Test generate_ics works without recurrence."""
        event = {
            "uid": "evt-no-rrule",
            "title": "Single Event",
            "start": "20261015T090000Z",
            "end": "20261015T110000Z",
            "room": "H1.1",
            "recurrence": "",
        }

        ics_content = schedule_sync_engine.generate_ics(event)

        # Should not contain RRULE
        assert "RRULE:" not in ics_content
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content

    async def test_handle_schedule_change(self, schedule_sync_engine):
        """Test handle_schedule_change detects affected students."""
        async with schedule_sync_engine:
            change_event = {
                "type": "schedule_update",
                "course_id": "LV-001",
                "event_id": "evt-001",
            }

            result = await schedule_sync_engine.handle_schedule_change(change_event)

            assert result["event_type"] == "schedule_update"
            assert result["course_id"] == "LV-001"
            assert result["event_id"] == "evt-001"
            assert "affected_user_ids" in result
            assert "user_count" in result
            assert isinstance(result["affected_user_ids"], list)

    async def test_handle_schedule_change_empty(self, schedule_sync_engine):
        """Test handle_schedule_change with empty course."""
        async with schedule_sync_engine:
            change_event = {
                "type": "schedule_update",
                "course_id": "non-existent",
                "event_id": "evt-999",
            }

            result = await schedule_sync_engine.handle_schedule_change(change_event)

            assert result["user_count"] == 0
            assert len(result["affected_user_ids"]) == 0


@pytest.mark.asyncio
class TestScheduleSyncEngineIntegration:
    """Integration tests for ScheduleSyncEngine."""

    async def test_full_sync_workflow_mock(self, schedule_sync_engine):
        """Test full sync workflow in mock mode."""
        async with schedule_sync_engine:
            # Get schedule
            schedule = await schedule_sync_engine.get_schedule("student-001", "2026ws")
            assert len(schedule) >= 5

            # Generate ICS for first event
            ics_content = schedule_sync_engine.generate_ics(schedule[0])
            assert "BEGIN:VCALENDAR" in ics_content

            # Attempt sync (should skip due to CalDAV not configured)
            sync_result = await schedule_sync_engine.sync_schedule_to_calendars(
                "student-001", "2026ws"
            )
            assert sync_result["status"] == "skipped"


@pytest.mark.asyncio
class TestScheduleSyncEngineErrorHandling:
    """Test error handling in ScheduleSyncEngine."""

    def test_generate_ics_missing_fields(self, schedule_sync_engine):
        """Test generate_ics handles missing fields gracefully."""
        event = {
            "uid": "evt-minimal",
            "title": "",
            "start": "",
            "end": "",
            "room": "",
            "recurrence": "",
        }

        ics_content = schedule_sync_engine.generate_ics(event)

        # Should still generate valid ICS structure
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
