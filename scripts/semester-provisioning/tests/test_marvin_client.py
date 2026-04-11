# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Marvin API client."""

import pytest
import httpx
from api.utils.marvin_client import MarvinClient, MarvinClientError


@pytest.fixture
def marvin_client():
    """Create a Marvin client for testing."""
    return MarvinClient(
        base_url="https://marvin.example.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""

    class MockResponse:
        def __init__(self, status_code: int, json_data: dict):
            self.status_code = status_code
            self._json_data = json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    request=httpx.Request("GET", "https://test"),
                    response=self,
                )

        def json(self):
            return self._json_data

    return MockResponse


class TestMarvinClientInitialization:
    """Test Marvin client initialization."""

    def test_client_init_with_values(self):
        """Test client initialization with provided values."""
        client = MarvinClient(
            base_url="https://marvin.example.com",
            client_id="test-id",
            client_secret="test-secret",
        )
        assert client.base_url == "https://marvin.example.com"
        assert client.client_id == "test-id"
        assert client.client_secret == "test-secret"

    def test_client_init_with_defaults(self):
        """Test client initialization uses settings when values not provided."""
        from unittest.mock import patch
        from api.config.settings import get_settings

        with patch("api.utils.marvin_client.get_settings") as mock_settings:
            mock_settings.return_value.configure_mock(
                marvin_api_url="https://marvin.example.com",
                marvin_client_id="settings-id",
                marvin_client_secret="settings-secret",
            )

            client = MarvinClient()
            assert client.base_url == "https://marvin.example.com"
            assert client.client_id == "settings-id"
            assert client.client_secret == "settings-secret"


class TestMarvinClientConfiguration:
    """Test Marvin client configuration checks."""

    def test_is_configured_with_all_values(self):
        """Test _is_configured returns True when all values present."""
        client = MarvinClient(
            base_url="https://marvin.example.com",
            client_id="test-id",
            client_secret="test-secret",
        )
        assert client._is_configured() is True

    def test_is_configured_with_missing_values(self):
        """Test _is_configured returns False when values missing."""
        client = MarvinClient(base_url=None, client_id=None, client_secret=None)
        assert client._is_configured() is False


class TestMarvinClientOAuthAuthentication:
    """Test OAuth 2.0 authentication."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_response):
        """Test successful OAuth 2.0 token refresh."""
        client = MarvinClient(
            base_url="https://marvin.example.com",
            client_id="test-id",
            client_secret="test-secret",
        )
        mock_response.status_code = 200
        mock_response._json_data = {"access_token": "test-token-123"}

        with patch.object(client._client, "post", return_value=mock_response):
            await client._refresh_token()
            assert client._access_token == "test-token-123"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self):
        """Test OAuth 2.0 token refresh raises error on failure."""
        client = MarvinClient(
            base_url="https://marvin.example.com",
            client_id="test-id",
            client_secret="test-secret",
        )

        with patch.object(client._client, "post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Token request failed",
                request=None,
                response=httpx.Response(500, request=None),
            )

            with pytest.raises(MarvinClientError) as exc_info:
                await client._refresh_token()
                assert "OAuth 2.0 token request failed" in str(exc_info.value)


class TestMarvinClientAPICalls:
    """Test Marvin API call methods."""

    @pytest.mark.asyncio
    async def test_get_semesters(self, marvin_client):
        """Test retrieving semesters from Marvin."""
        with patch.object(marvin_client, "_api_call") as mock_api_call:
            mock_api_call.return_value = {
                "data": [
                    {"id": "20261", "name": "Winter Semester 2026/2027"},
                    {"id": "20262", "name": "Summer Semester 2027"},
                ]
            }

            result = await marvin_client.get_semesters()
            assert result == {
                "data": [
                    {"id": "20261", "name": "Winter Semester 2026/2027"},
                    {"id": "20262", "name": "Summer Semester 2027"},
                ]
            }

    @pytest.mark.asyncio
    async def test_get_courses(self, marvin_client):
        """Test retrieving courses for a semester."""
        with patch.object(marvin_client, "_api_call") as mock_api_call:
            mock_api_call.return_value = {
                "data": [
                    {"id": "course-001", "name": "Introduction to Computer Science"},
                ]
            }

            result = await marvin_client.get_courses("20261")
            mock_api_call.assert_called_once()
            assert result == {
                "data": [
                    {"id": "course-001", "name": "Introduction to Computer Science"},
                ]
            }

    @pytest.mark.asyncio
    async def test_get_enrollments(self, marvin_client):
        """Test retrieving course enrollments."""
        with patch.object(marvin_client, "_api_call") as mock_api_call:
            mock_api_call.return_value = {
                "data": [
                    {"id": "enr-001", "student_id": "student-001", "role": "student"}
                ]
            }

            result = await marvin_client.get_enrollments("course-001")
            assert result == {
                "data": [
                    {"id": "enr-001", "student_id": "student-001", "role": "student"}
                ]
            }

    @pytest.mark.asyncio
    async def test_get_student(self, marvin_client):
        """Test retrieving student attributes."""
        with patch.object(marvin_client, "_api_call") as mock_api_call:
            mock_api_call.return_value = {
                "data": {
                    "id": "student-001",
                    "first_name": "Max",
                    "last_name": "Mustermann",
                    "email": "max.mustermann@example.de",
                }
            }

            result = await marvin_client.get_student("student-001")
            assert result == {
                "data": {
                    "id": "student-001",
                    "first_name": "Max",
                    "last_name": "Mustermann",
                    "email": "max.mustermann@example.de",
                }
            }


class TestMarvinClientMockData:
    """Test mock data fallback when API not configured."""

    @pytest.mark.asyncio
    async def test_get_semesters_returns_mock_data(self):
        """Test mock data when API not configured."""
        client = MarvinClient(base_url=None)
        result = await client.get_semesters()
        assert result == {
            "data": [
                {"id": "20261", "name": "Winter Semester 2026/2027"},
                {"id": "20262", "name": "Summer Semester 2027"},
            ]
        }

    @pytest.mark.asyncio
    async def test_get_courses_returns_mock_data(self):
        """Test mock course data when API not configured."""
        client = MarvinClient(base_url=None)
        result = await client.get_courses("20261")
        assert result == {
            "data": [
                {
                    "id": "course-001",
                    "name": "Introduction to Computer Science",
                    "semester": "20261",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_api_call_without_configuration(self, caplog):
        """Test API call raises error when client not configured."""
        client = MarvinClient(base_url="https://test.com")
        client._access_token = "test-token"

        with pytest.raises(MarvinClientError) as exc_info:
            result = await client._api_call("GET", "/api/v1/semesters")
            assert result is None

    @pytest.mark.asyncio
    async def test_api_call_without_client_initialization(self):
        """Test API call raises error when client not initialized."""
        client = MarvinClient(base_url="https://test.com")
        client._access_token = "test-token"

        with pytest.raises(MarvinClientError) as exc_info:
            result = await client._api_call("GET", "/api/v1/semesters")
            assert "Client not initialized" in str(exc_info.value)
