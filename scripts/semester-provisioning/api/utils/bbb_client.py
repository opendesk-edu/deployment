# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
from typing import Any, Optional
import hashlib
import httpx

from api.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class BBBClientError(Exception):
    """Exception raised for BBB API errors."""

    pass


class BBBClient:
    """BigBlueButton (BBB) API client.

    Implements BBB REST API with checksum authentication.
    Falls back to mock data when no API URL/secret are configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """Initialize BBB client with credentials.

        Args:
            base_url: BBB API base URL
            secret: BBB API secret key
        """
        settings = get_settings()
        self.base_url = base_url or settings.bbb_url
        self.secret = secret or settings.bbb_secret
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BBBClient":
        """Initialize HTTP client."""
        url = self.base_url if self.base_url else "https://bbb.opendesk.edu"
        self._client = httpx.AsyncClient(base_url=url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    def _is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.base_url and self.secret)

    def _generate_checksum(self, method_name: str, params: str) -> str:
        """Generate BBB API checksum.

        Args:
            method_name: BBB API method name
            params: URL-encoded query parameters string

        Returns:
            SHA1 checksum
        """
        # BBB checksum: sha1(method_name + params + secret)
        checksum_string = f"{method_name}{params}{self.secret}"
        checksum = hashlib.sha1(checksum_string.encode()).hexdigest()
        return checksum

    def _build_params_string(self, params: dict[str, Any]) -> str:
        """Build URL-encoded query string from params dict.

        Args:
            params: Dictionary of parameters

        Returns:
            URL-encoded query string
        """
        # Convert params to query string
        param_strings = []
        for key, value in sorted(params.items()):
            if value is not None:
                # URL encode both key and value
                import urllib.parse

                encoded_key = urllib.parse.quote(str(key))
                encoded_value = urllib.parse.quote(str(value))
                param_strings.append(f"{encoded_key}={encoded_value}")

        return "&".join(param_strings)

    async def _call_api(
        self, method_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a BBB API call.

        Args:
            method_name: BBB API method name
            params: API parameters

        Returns:
            Parsed response data

        Raises:
            BBBClientError: If API call fails
        """
        if not self._is_configured():
            logger.info("BBB API not configured, returning mock data")
            return self._get_mock_data(method_name, params)

        if not self._client:
            raise BBBClientError("Client not initialized. Use async context manager.")

        # Build params string and checksum
        params_string = self._build_params_string(params)
        checksum = self._generate_checksum(method_name, params_string)

        # Build full URL
        api_url = (
            f"/bigbluebutton/api/{method_name}?{params_string}&checksum={checksum}"
        )

        try:
            response = await self._client.get(api_url)
            response.raise_for_status()

            # Parse XML response
            return self._parse_response(response.text)

        except httpx.HTTPStatusError as e:
            raise BBBClientError(f"BBB API call failed: {e}")

    def _parse_response(self, xml_response: str) -> dict[str, Any]:
        """Parse BBB XML response.

        Args:
            xml_response: Raw XML response string

        Returns:
            Parsed response as dictionary
        """
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_response)

            # Extract returncode
            returncode = root.find("returncode")
            if returncode is not None and returncode.text == "SUCCESS":
                result = {"success": True}

                # Extract all children
                for child in root:
                    if child.tag != "returncode":
                        # Handle nested elements
                        if len(child) > 0:
                            child_dict = {}
                            for subchild in child:
                                child_dict[subchild.tag] = subchild.text
                            result[child.tag] = child_dict
                        else:
                            result[child.tag] = child.text

                return result
            else:
                message = root.find("message")
                message_text = message.text if message is not None else "Unknown error"
                return {"success": False, "message": message_text}

        except Exception as e:
            logger.warning(f"Failed to parse BBB response: {e}")
            return {"success": False, "message": str(e)}

    def _get_mock_data(
        self, method_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Return mock data for development/testing.

        Args:
            method_name: BBB API method name
            params: Method parameters

        Returns:
            Mock response data
        """
        meeting_id = params.get("meetingID", "test-meeting")

        if method_name == "create":
            return {
                "success": True,
                "meetingID": meeting_id,
                "internalMeetingID": f"internal-{meeting_id}",
                "meetingName": params.get("name", "Test Meeting"),
                "moderatorPW": params.get("moderatorPW", "mod"),
                "attendeePW": params.get("attendeePW", "attend"),
                "createTime": "1234567890",
                "voiceBridge": "70000",
                "dialNumber": "613-555-1234",
                "createDate": "Thu Jan 01 00:00:00 UTC 1970",
                "hasUserJoined": False,
                "duration": 0,
                "maxParticipants": params.get("maxParticipants", 50),
            }

        elif method_name == "getMeetingInfo":
            return {
                "success": True,
                "meetingID": meeting_id,
                "meetingName": params.get("name", "Test Meeting"),
                "meetingRunning": True,
                "moderatorCount": 1,
                "participantCount": 0,
                "listeners": 0,
                "voiceParticipants": 0,
                "videoCount": 0,
                "duration": 0,
                "hasUserJoined": False,
                "isRecording": False,
                "hasBeenForciblyEnded": False,
                "startTime": 1234567890000,
                "endTime": 0,
                "maxParticipants": params.get("maxParticipants", 50),
            }

        elif method_name == "end":
            return {
                "success": True,
                "message": "Meeting ended successfully",
            }

        elif method_name == "isMeetingRunning":
            return {
                "success": True,
                "running": False,
            }

        return {"success": False, "message": "Unknown method"}

    async def create_meeting(self, meeting_params: dict[str, Any]) -> dict[str, Any]:
        """Create a BBB meeting.

        Args:
            meeting_params: Meeting parameters including:
                - name: Meeting name
                - meetingID: Meeting ID
                - attendeePW: Attendee password
                - moderatorPW: Moderator password
                - maxParticipants: Maximum participants

        Returns:
            Meeting creation result
        """
        logger.info(f"Creating BBB meeting: {meeting_params.get('name', 'unnamed')}")
        return await self._call_api("create", meeting_params)

    async def get_meeting_info(self, meeting_id: str) -> dict[str, Any]:
        """Get BBB meeting information.

        Args:
            meeting_id: Meeting ID

        Returns:
            Meeting information
        """
        logger.info(f"Getting BBB meeting info: {meeting_id}")
        return await self._call_api("getMeetingInfo", {"meetingID": meeting_id})

    async def end_meeting(self, meeting_id: str) -> bool:
        """End a BBB meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            True if meeting was ended successfully
        """
        logger.info(f"Ending BBB meeting: {meeting_id}")
        result = await self._call_api("end", {"meetingID": meeting_id})
        return result.get("success", False)

    async def is_meeting_running(self, meeting_id: str) -> bool:
        """Check if a BBB meeting is running.

        Args:
            meeting_id: Meeting ID

        Returns:
            True if meeting is running, False otherwise
        """
        result = await self._call_api("isMeetingRunning", {"meetingID": meeting_id})
        return result.get("running", False)
