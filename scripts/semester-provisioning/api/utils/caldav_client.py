# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
from typing import Any, Optional
import httpx
from api.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class CalDAVClientError(Exception):
    """Exception raised for CalDAV client errors."""

    pass


class CalDAVClient:
    """CalDAV client for SOGo calendar management.

    Provides CRUD operations for calendar events via CalDAV protocol.
    Falls back to mock data when credentials are not configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ):
        """Initialize CalDAV client with credentials.

        Args:
            base_url: CalDAV server base URL
            username: CalDAV username
            password: CalDAV password
            verify_ssl: Whether to verify SSL certificates
        """
        settings = get_settings()
        self.base_url = base_url or settings.caldav_url
        self.username = username or settings.caldav_username
        self.password = password or settings.caldav_password
        self.verify_ssl = (
            verify_ssl if verify_ssl is not None else settings.caldav_verify_ssl
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._mock_events: dict[str, list[dict]] = {}

    async def __aenter__(self) -> "CalDAVClient":
        """Initialize HTTP client."""
        if self._is_configured():
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(self.username, self.password),
                verify=self.verify_ssl,
                timeout=30.0,
            )
            logger.info("CalDAV client initialized")
        else:
            logger.warning("CalDAV credentials not configured, using mock mode")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    def _is_configured(self) -> bool:
        """Check if CalDAV credentials are configured."""
        return bool(self.base_url and self.username and self.password)

    def _normalize_calendar_path(self, calendar_path: str) -> str:
        """Normalize calendar path to ensure proper format.

        Args:
            calendar_path: Calendar path (e.g., "/dav/user/calendar/")

        Returns:
            Normalized calendar path
        """
        if not calendar_path.startswith("/"):
            calendar_path = f"/{calendar_path}"
        if not calendar_path.endswith("/"):
            calendar_path += "/"
        return calendar_path

    async def create_event(
        self, calendar_path: str, event_uid: str, ics_content: str
    ) -> bool:
        """Create a new calendar event.

        Args:
            calendar_path: Calendar path (e.g., "/dav/user/calendar/")
            event_uid: Unique event identifier
            ics_content: ICS format event content

        Returns:
            True if successful, False otherwise
        """
        if not self._is_configured():
            logger.info(f"Mock mode: creating event {event_uid}")
            calendar_path = self._normalize_calendar_path(calendar_path)
            if calendar_path not in self._mock_events:
                self._mock_events[calendar_path] = []

            # Check if event already exists
            for event in self._mock_events[calendar_path]:
                if event.get("uid") == event_uid:
                    logger.warning(f"Event {event_uid} already exists")
                    return False

            # Add mock event
            self._mock_events[calendar_path].append(
                {
                    "uid": event_uid,
                    "ics": ics_content,
                    "href": f"{calendar_path}{event_uid}.ics",
                }
            )
            return True

        if not self._client:
            raise CalDAVClientError(
                "Client not initialized. Use async context manager."
            )

        calendar_path = self._normalize_calendar_path(calendar_path)
        event_path = f"{calendar_path}{event_uid}.ics"

        try:
            response = await self._client.put(
                event_path,
                content=ics_content.encode("utf-8"),
                headers={"Content-Type": "text/calendar; charset=utf-8"},
            )
            response.raise_for_status()

            logger.info(f"Created CalDAV event {event_uid} at {event_path}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create CalDAV event {event_uid}: {e}")
            return False

    async def update_event(
        self, calendar_path: str, event_uid: str, ics_content: str
    ) -> bool:
        """Update an existing calendar event.

        Args:
            calendar_path: Calendar path (e.g., "/dav/user/calendar/")
            event_uid: Unique event identifier
            ics_content: Updated ICS format event content

        Returns:
            True if successful, False otherwise
        """
        if not self._is_configured():
            logger.info(f"Mock mode: updating event {event_uid}")
            calendar_path = self._normalize_calendar_path(calendar_path)

            # Find and update event
            if calendar_path in self._mock_events:
                for event in self._mock_events[calendar_path]:
                    if event.get("uid") == event_uid:
                        event["ics"] = ics_content
                        logger.info(f"Updated mock event {event_uid}")
                        return True

            logger.warning(f"Event {event_uid} not found for update")
            return False

        if not self._client:
            raise CalDAVClientError(
                "Client not initialized. Use async context manager."
            )

        calendar_path = self._normalize_calendar_path(calendar_path)
        event_path = f"{calendar_path}{event_uid}.ics"

        try:
            response = await self._client.put(
                event_path,
                content=ics_content.encode("utf-8"),
                headers={"Content-Type": "text/calendar; charset=utf-8"},
            )
            response.raise_for_status()

            logger.info(f"Updated CalDAV event {event_uid} at {event_path}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update CalDAV event {event_uid}: {e}")
            return False

    async def delete_event(self, calendar_path: str, event_uid: str) -> bool:
        """Delete a calendar event.

        Args:
            calendar_path: Calendar path (e.g., "/dav/user/calendar/")
            event_uid: Unique event identifier

        Returns:
            True if successful, False otherwise
        """
        if not self._is_configured():
            logger.info(f"Mock mode: deleting event {event_uid}")
            calendar_path = self._normalize_calendar_path(calendar_path)

            # Find and remove event
            if calendar_path in self._mock_events:
                self._mock_events[calendar_path] = [
                    e
                    for e in self._mock_events[calendar_path]
                    if e.get("uid") != event_uid
                ]
                logger.info(f"Deleted mock event {event_uid}")
                return True

            logger.warning(f"Event {event_uid} not found for deletion")
            return False

        if not self._client:
            raise CalDAVClientError(
                "Client not initialized. Use async context manager."
            )

        calendar_path = self._normalize_calendar_path(calendar_path)
        event_path = f"{calendar_path}{event_uid}.ics"

        try:
            response = await self._client.delete(event_path)
            response.raise_for_status()

            logger.info(f"Deleted CalDAV event {event_uid} at {event_path}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete CalDAV event {event_uid}: {e}")
            return False

    async def list_events(self, calendar_path: str) -> list[dict]:
        """List all events in a calendar.

        Args:
            calendar_path: Calendar path (e.g., "/dav/user/calendar/")

        Returns:
            List of event dictionaries with uid and href
        """
        if not self._is_configured():
            logger.info(f"Mock mode: listing events in {calendar_path}")
            calendar_path = self._normalize_calendar_path(calendar_path)

            if calendar_path not in self._mock_events:
                self._mock_events[calendar_path] = []

            return [
                {"uid": event["uid"], "href": event["href"]}
                for event in self._mock_events[calendar_path]
            ]

        if not self._client:
            raise CalDAVClientError(
                "Client not initialized. Use async context manager."
            )

        calendar_path = self._normalize_calendar_path(calendar_path)

        try:
            # PROPFIND request to list events
            propfind_body = """<?xml version="1.0" encoding="utf-8" ?>
<D:propfind xmlns:D="DAV:">
    <D:prop>
        <D:getetag/>
        <D:displayname/>
    </D:prop>
</D:propfind>"""

            response = await self._client.request(
                "PROPFIND",
                calendar_path,
                content=propfind_body.encode("utf-8"),
                headers={
                    "Content-Type": "application/xml; charset=utf-8",
                    "Depth": "1",
                },
            )
            response.raise_for_status()

            # Parse PROPFIND response
            events = self._parse_propfind_response(response.text)
            logger.info(f"Listed {len(events)} events from {calendar_path}")
            return events

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list events from {calendar_path}: {e}")
            return []

    def _parse_propfind_response(self, xml_response: str) -> list[dict]:
        """Parse CalDAV PROPFIND XML response.

        Args:
            xml_response: Raw XML response string

        Returns:
            List of event dictionaries with uid and href
        """
        # Simple XML parser for CalDAV PROPFIND responses
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_response)

            # Find all response elements
            namespaces = {"D": "DAV:"}
            events = []

            for response in root.findall(".//D:response", namespaces):
                href = response.find("D:href", namespaces)
                if href is not None:
                    href_text = href.text or ""

                    # Extract UID from href (format: /path/uid.ics)
                    if href_text.endswith(".ics"):
                        event_uid = href_text.rstrip(".ics").split("/")[-1]
                        events.append({"uid": event_uid, "href": href_text})

            return events

        except Exception as e:
            logger.warning(f"Failed to parse PROPFIND response: {e}")
            return []
