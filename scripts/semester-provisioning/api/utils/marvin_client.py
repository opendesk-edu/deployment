# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
from typing import Any, List, Optional

import httpx
from api.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class MarvinClientError(Exception):
    """Exception raised for Marvin API errors."""

    pass


class MarvinClient:
    """Marvin REST API client.

    Implements Marvin API with OAuth 2.0 client credentials flow.
    Falls back to mock data when no API URL/credentials are configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """Initialize Marvin client with OAuth 2.0 credentials."""
        settings = get_settings()
        self.base_url = base_url or settings.marvin_api_url
        self.client_id = client_id or settings.marvin_client_id
        self.client_secret = client_secret or settings.marvin_client_secret
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def __aenter__(self) -> "MarvinClient":
        """Initialize HTTP client and authenticate."""
        url = self.base_url if self.base_url else "http://localhost"
        self._client = httpx.AsyncClient(base_url=url, timeout=30.0)
        await self._refresh_token()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    def _is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.base_url and self.client_id and self.client_secret)

    async def _refresh_token(self) -> None:
        """OAuth 2.0 client credentials grant to get access token."""
        if not self._is_configured():
            logger.warning(
                "Marvin API URL and credentials not configured, using mock mode"
            )
            self._access_token = "mock-token"
            return

        if not self._client:
            raise MarvinClientError(
                "Client not initialized. Use async context manager."
            )

        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = await self._client.post("/oauth2/token", data=params)
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get("access_token")
            logger.info("Successfully obtained Marvin OAuth 2.0 access token")
        except httpx.HTTPStatusError as e:
            raise MarvinClientError(f"OAuth 2.0 token request failed: {e}")
        except (KeyError, ValueError) as e:
            raise MarvinClientError(f"Invalid token response: {e}")

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make authenticated API call to Marvin."""
        if not self._is_configured():
            logger.info("Marvin API not configured, returning mock data")
            return self._get_mock_data(endpoint)

        if not self._client:
            raise MarvinClientError(
                "Client not initialized. Use async context manager."
            )

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._client.request(
                method, endpoint, headers=headers, params=params, json=json
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Token expired? Refresh and retry once
            if e.response.status_code == 401:
                logger.info("Access token expired, refreshing...")
                await self._refresh_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                response = await self._client.request(
                    method, endpoint, headers=headers, params=params, json=json
                )
                response.raise_for_status()
                return response.json()
            raise MarvinClientError(f"API call failed: {e}")

    async def get_semesters(self) -> List[dict]:
        """List active semesters."""
        return await self._api_call("GET", "/api/v1/semesters")

    async def get_courses(self, semester_code: str) -> List[dict]:
        """Get courses for semester."""
        return await self._api_call("GET", f"/api/v1/courses?semester={semester_code}")

    async def get_enrollments(self, course_id: str) -> List[dict]:
        """Get course enrollments."""
        return await self._api_call("GET", f"/api/v1/courses/{course_id}/enrollments")

    async def get_student(self, student_id: str) -> dict:
        """Get student attributes."""
        return await self._api_call("GET", f"/api/v1/students/{student_id}")

    def _get_mock_data(self, endpoint: str) -> dict[str, Any]:
        """Return mock data for development/testing."""
        if "/semesters" in endpoint:
            return {
                "data": [
                    {"id": "20261", "name": "Winter Semester 2026/2027"},
                    {"id": "20262", "name": "Summer Semester 2027"},
                ]
            }
        elif "/courses" in endpoint:
            return {
                "data": [
                    {
                        "id": "course-001",
                        "name": "Introduction to Computer Science",
                        "semester": "20261",
                    }
                ]
            }
        elif "/enrollments" in endpoint:
            return {
                "data": [
                    {"id": "enr-001", "student_id": "student-001", "role": "student"}
                ]
            }
        elif "/students" in endpoint:
            return {
                "data": {
                    "id": "student-001",
                    "first_name": "Max",
                    "last_name": "Mustermann",
                    "email": "max.mustermann@example.de",
                }
            }
        return {"data": []}
