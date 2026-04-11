# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
import pytest
from api.utils.caldav_client import CalDAVClient, CalDAVClientError


@pytest.fixture
def caldav_client():
    """Create CalDAVClient instance for testing."""
    return CalDAVClient()


@pytest.fixture
def sample_ics_content():
    """Sample ICS content for testing."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//openDesk Edu//Schedule Sync//EN
BEGIN:VEVENT
UID:evt-001
SUMMARY:Einführung in die Informatik
DTSTART:20261015T090000Z
DTEND:20261015T110000Z
LOCATION:H1.1
DTSTAMP:20261015T120000Z
RRULE:FREQ=WEEKLY;BYDAY=MO,FR
END:VEVENT
END:VCALENDAR"""


@pytest.mark.asyncio
class TestCalDAVClientMockMode:
    """Test CalDAVClient in mock mode."""

    async def test_initialization(self, caldav_client):
        """Test client initialization."""
        assert caldav_client.base_url == ""
        assert caldav_client.username == ""
        assert caldav_client.password == ""
        assert caldav_client.verify_ssl is True

    async def test_is_configured(self, caldav_client):
        """Test configuration check."""
        # Should return False when credentials are empty
        assert not caldav_client._is_configured()

    async def test_is_configured_with_credentials(self):
        """Test configuration check with credentials."""
        client = CalDAVClient(
            base_url="https://sogo.opendesk.edu/dav/",
            username="testuser",
            password="testpass",
        )
        assert client._is_configured()

    async def test_context_manager(self, caldav_client):
        """Test async context manager."""
        async with caldav_client:
            # Should not raise error
            pass

    async def test_create_event_mock(self, caldav_client, sample_ics_content):
        """Test create_event in mock mode."""
        async with caldav_client:
            result = await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )
            assert result is True

    async def test_create_event_duplicate(self, caldav_client, sample_ics_content):
        """Test create_event returns False for duplicate events."""
        async with caldav_client:
            # Create first event
            result1 = await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )
            assert result1 is True

            # Try to create duplicate
            result2 = await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )
            assert result2 is False

    async def test_update_event_mock(self, caldav_client, sample_ics_content):
        """Test update_event in mock mode."""
        async with caldav_client:
            # First create an event
            await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )

            # Then update it
            updated_ics = sample_ics_content.replace(
                "SUMMARY:Einführung", "SUMMARY:Updated"
            )
            result = await caldav_client.update_event(
                "/dav/user-001/calendar/", "evt-001", updated_ics
            )
            assert result is True

    async def test_update_event_not_found(self, caldav_client, sample_ics_content):
        """Test update_event returns False for non-existent event."""
        async with caldav_client:
            result = await caldav_client.update_event(
                "/dav/user-001/calendar/", "evt-999", sample_ics_content
            )
            assert result is False

    async def test_delete_event_mock(self, caldav_client, sample_ics_content):
        """Test delete_event in mock mode."""
        async with caldav_client:
            # First create an event
            await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )

            # Then delete it
            result = await caldav_client.delete_event(
                "/dav/user-001/calendar/", "evt-001"
            )
            assert result is True

    async def test_delete_event_not_found(self, caldav_client):
        """Test delete_event returns False for non-existent event."""
        async with caldav_client:
            result = await caldav_client.delete_event(
                "/dav/user-001/calendar/", "evt-999"
            )
            assert result is False

    async def test_list_events_mock(self, caldav_client, sample_ics_content):
        """Test list_events in mock mode."""
        async with caldav_client:
            # Create some events
            await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )
            await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-002", sample_ics_content
            )

            # List events
            events = await caldav_client.list_events("/dav/user-001/calendar/")
            assert len(events) == 2

            # Check event structure
            assert events[0]["uid"] == "evt-001"
            assert events[1]["uid"] == "evt-002"
            assert "href" in events[0]
            assert "href" in events[1]

    async def test_list_events_empty(self, caldav_client):
        """Test list_events returns empty list when no events."""
        async with caldav_client:
            events = await caldav_client.list_events("/dav/user-999/calendar/")
            assert events == []

    async def test_normalize_calendar_path(self, caldav_client):
        """Test calendar path normalization."""
        # Path without leading slash
        path1 = caldav_client._normalize_calendar_path("dav/user/calendar/")
        assert path1 == "/dav/user/calendar/"

        # Path without trailing slash
        path2 = caldav_client._normalize_calendar_path("/dav/user/calendar")
        assert path2 == "/dav/user/calendar/"

        # Path without both slashes
        path3 = caldav_client._normalize_calendar_path("dav/user/calendar")
        assert path3 == "/dav/user/calendar/"

        # Path with both slashes (unchanged)
        path4 = caldav_client._normalize_calendar_path("/dav/user/calendar/")
        assert path4 == "/dav/user/calendar/"


@pytest.mark.asyncio
class TestCalDAVClientCRUDWorkflow:
    """Test full CRUD workflow in mock mode."""

    async def test_full_crud_workflow(self, caldav_client, sample_ics_content):
        """Test create, read, update, delete workflow."""
        async with caldav_client:
            calendar_path = "/dav/user-001/calendar/"

            # Create event
            create_result = await caldav_client.create_event(
                calendar_path, "evt-workflow", sample_ics_content
            )
            assert create_result is True

            # List events to verify creation
            events = await caldav_client.list_events(calendar_path)
            assert len(events) == 1
            assert events[0]["uid"] == "evt-workflow"

            # Update event
            updated_ics = sample_ics_content.replace(
                "SUMMARY:Einführung", "SUMMARY:Updated"
            )
            update_result = await caldav_client.update_event(
                calendar_path, "evt-workflow", updated_ics
            )
            assert update_result is True

            # Verify event still exists after update
            events = await caldav_client.list_events(calendar_path)
            assert len(events) == 1

            # Delete event
            delete_result = await caldav_client.delete_event(
                calendar_path, "evt-workflow"
            )
            assert delete_result is True

            # Verify event was deleted
            events = await caldav_client.list_events(calendar_path)
            assert len(events) == 0


@pytest.mark.asyncio
class TestCalDAVClientMultipleCalendars:
    """Test handling multiple calendars."""

    async def test_separate_calendars(self, caldav_client, sample_ics_content):
        """Test events are kept separate across different calendars."""
        async with caldav_client:
            # Create event in first calendar
            await caldav_client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )

            # Create event in second calendar
            await caldav_client.create_event(
                "/dav/user-002/calendar/", "evt-002", sample_ics_content
            )

            # List events from both calendars
            events1 = await caldav_client.list_events("/dav/user-001/calendar/")
            events2 = await caldav_client.list_events("/dav/user-002/calendar/")

            assert len(events1) == 1
            assert len(events2) == 1
            assert events1[0]["uid"] == "evt-001"
            assert events2[0]["uid"] == "evt-002"


@pytest.mark.asyncio
class TestCalDAVClientErrorHandling:
    """Test error handling in CalDAVClient."""

    async def test_create_event_without_context_manager(
        self, caldav_client, sample_ics_content
    ):
        """Test that operations fail without context manager when configured."""
        # Configure client with credentials
        client = CalDAVClient(
            base_url="https://sogo.opendesk.edu/dav/",
            username="testuser",
            password="testpass",
        )

        # Should raise error without context manager
        with pytest.raises(CalDAVClientError, match="not initialized"):
            await client.create_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )

    async def test_update_event_without_context_manager(
        self, caldav_client, sample_ics_content
    ):
        """Test that operations fail without context manager when configured."""
        client = CalDAVClient(
            base_url="https://sogo.opendesk.edu/dav/",
            username="testuser",
            password="testpass",
        )

        with pytest.raises(CalDAVClientError, match="not initialized"):
            await client.update_event(
                "/dav/user-001/calendar/", "evt-001", sample_ics_content
            )

    async def test_delete_event_without_context_manager(self, caldav_client):
        """Test that operations fail without context manager when configured."""
        client = CalDAVClient(
            base_url="https://sogo.opendesk.edu/dav/",
            username="testuser",
            password="testpass",
        )

        with pytest.raises(CalDAVClientError, match="not initialized"):
            await client.delete_event("/dav/user-001/calendar/", "evt-001")

    async def test_list_events_without_context_manager(self, caldav_client):
        """Test that operations fail without context manager when configured."""
        client = CalDAVClient(
            base_url="https://sogo.opendesk.edu/dav/",
            username="testuser",
            password="testpass",
        )

        with pytest.raises(CalDAVClientError, match="not initialized"):
            await client.list_events("/dav/user-001/calendar/")
