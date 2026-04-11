# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
import pytest
from api.utils.bbb_client import BBBClient, BBBClientError


@pytest.mark.asyncio
async def test_bbb_client_mock_mode():
    """Test BBBClient in mock mode."""
    client = BBBClient()

    # Mock mode should work without credentials
    assert not client._is_configured()


@pytest.mark.asyncio
async def test_bbb_client_create_meeting():
    """Test creating a BBB meeting."""
    async with BBBClient() as client:
        meeting_params = {
            "name": "Test Meeting",
            "meetingID": "test-meeting-123",
            "attendeePW": "attendee",
            "moderatorPW": "mod",
            "maxParticipants": 50,
        }

        result = await client.create_meeting(meeting_params)

        # Mock response should be successful
        assert result["success"] is True
        assert result["meetingID"] == "test-meeting-123"
        assert result["meetingName"] == "Test Meeting"
        assert result["maxParticipants"] == 50


@pytest.mark.asyncio
async def test_bbb_client_get_meeting_info():
    """Test getting BBB meeting information."""
    async with BBBClient() as client:
        result = await client.get_meeting_info("test-meeting-123")

        # Mock response should be successful
        assert result["success"] is True
        assert result["meetingID"] == "test-meeting-123"


@pytest.mark.asyncio
async def test_bbb_client_end_meeting():
    """Test ending a BBB meeting."""
    async with BBBClient() as client:
        result = await client.end_meeting("test-meeting-123")

        # Mock response should be successful
        assert result is True


@pytest.mark.asyncio
async def test_bbb_client_is_meeting_running():
    """Test checking if a BBB meeting is running."""
    async with BBBClient() as client:
        result = await client.is_meeting_running("test-meeting-123")

        # Mock response should be False
        assert result is False


def test_bbb_client_generate_checksum():
    """Test BBB checksum generation."""
    client = BBBClient()
    client.secret = "test-secret"

    # Test checksum generation
    checksum = client._generate_checksum(
        "create", "name=Test+Meeting&meetingID=test-123"
    )

    # Checksum should be a 40-character hex string
    assert len(checksum) == 40
    assert all(c in "0123456789abcdef" for c in checksum.lower())


def test_bbb_client_build_params_string():
    """Test building params string from dictionary."""
    client = BBBClient()

    params = {
        "name": "Test Meeting",
        "meetingID": "test-123",
        "maxParticipants": 50,
    }

    params_string = client._build_params_string(params)

    # Should be URL-encoded
    assert (
        "name=Test%20Meeting" in params_string or "name=Test+Meeting" in params_string
    )
    assert "meetingID=test-123" in params_string
    assert "maxParticipants=50" in params_string


def test_bbb_client_build_params_string_sorted():
    """Test that params string is sorted by key."""
    client = BBBClient()

    params = {
        "z_param": "z",
        "a_param": "a",
        "m_param": "m",
    }

    params_string = client._build_params_string(params)

    # Params should be sorted alphabetically
    parts = params_string.split("&")
    assert parts[0].startswith("a_param")
    assert parts[1].startswith("m_param")
    assert parts[2].startswith("z_param")


def test_bbb_client_build_params_string_with_none():
    """Test building params string with None values."""
    client = BBBClient()

    params = {
        "name": "Test",
        "maxParticipants": None,
        "duration": 60,
    }

    params_string = client._build_params_string(params)

    # None values should be omitted
    assert "name=Test" in params_string
    assert "duration=60" in params_string
    assert "maxParticipants" not in params_string


@pytest.mark.asyncio
async def test_bbb_client_context_manager():
    """Test BBBClient as async context manager."""
    async with BBBClient() as client:
        assert client is not None
        assert client._client is not None

        # Should be able to call methods
        result = await client.create_meeting(
            {
                "name": "Test",
                "meetingID": "test-123",
            }
        )
        assert result["success"] is True


@pytest.mark.asyncio
async def test_bbb_client_without_credentials():
    """Test BBBClient without credentials uses mock data."""
    # Create client without credentials
    client = BBBClient(base_url="", secret="")

    assert not client._is_configured()

    async with client:
        # Should return mock data
        result = await client.create_meeting(
            {
                "name": "Test",
                "meetingID": "test-123",
            }
        )
        assert result["success"] is True


@pytest.mark.asyncio
async def test_bbb_client_parse_response():
    """Test parsing BBB XML response."""
    client = BBBClient()

    xml_response = """<?xml version="1.0"?>
<response>
    <returncode>SUCCESS</returncode>
    <meetingID>test-123</meetingID>
    <meetingName>Test Meeting</meetingName>
</response>"""

    result = client._parse_response(xml_response)

    assert result["success"] is True
    assert result["meetingID"] == "test-123"
    assert result["meetingName"] == "Test Meeting"


@pytest.mark.asyncio
async def test_bbb_client_parse_response_error():
    """Test parsing BBB XML error response."""
    client = BBBClient()

    xml_response = """<?xml version="1.0"?>
<response>
    <returncode>FAILED</returncode>
    <message>Meeting not found</message>
</response>"""

    result = client._parse_response(xml_response)

    assert result["success"] is False
    assert result["message"] == "Meeting not found"


@pytest.mark.asyncio
async def test_bbb_client_create_meeting_with_all_params():
    """Test creating a BBB meeting with all parameters."""
    async with BBBClient() as client:
        meeting_params = {
            "name": "Full Test Meeting",
            "meetingID": "full-test-123",
            "attendeePW": "attend123",
            "moderatorPW": "mod123",
            "maxParticipants": 100,
            "duration": 60,
            "welcome": "Welcome!",
        }

        result = await client.create_meeting(meeting_params)

        # Mock response should include the provided params
        assert result["success"] is True
        assert result["meetingID"] == "full-test-123"
        assert result["meetingName"] == "Full Test Meeting"
        assert result["maxParticipants"] == 100
