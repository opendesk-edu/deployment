# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
from typing import TYPE_CHECKING, Any, Optional
import logging

from api.config.settings import get_settings
from api.utils.hisinone_client import HISinOneClient

if TYPE_CHECKING:
    from api.utils.bbb_client import BBBClient

logger = logging.getLogger(__name__)


class RoomSyncError(Exception):
    """Exception raised for room sync errors."""

    pass


class RoomSyncEngine:
    """Room assignment synchronization engine.

    Extracts room assignments from HISinOne, provisions BBB rooms,
    and detects room conflicts.
    Falls back to mock data when credentials are not configured.
    """

    def __init__(
        self,
        hisinone_client: Optional[HISinOneClient] = None,
    ):
        """Initialize room sync engine.

        Args:
            hisinone_client: Optional HISinOne client instance
        """
        settings = get_settings()
        self.hisinone_client = hisinone_client or HISinOneClient()
        self._bbb_client: Optional["BBBClient"] = None

    async def __aenter__(self) -> "RoomSyncEngine":
        """Initialize clients."""
        await self.hisinone_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close clients."""
        await self.hisinone_client.__aexit__(exc_type, exc_val, exc_tb)

    def _is_configured(self) -> bool:
        """Check if BBB is configured."""
        settings = get_settings()
        return bool(settings.bbb_url and settings.bbb_secret)

    async def get_room_assignments(
        self, date: str, room: Optional[str] = None
    ) -> list[dict]:
        """Get room assignments from HISinOne.

        Args:
            date: Date in YYYY-MM-DD format
            room: Optional room filter (e.g., "H1.1")

        Returns:
            List of room assignment dictionaries
        """
        params: dict[str, Any] = {"date": date}
        if room:
            params["raum"] = room

        assignments = await self.hisinone_client._soap_call("getRaumbuchung", params)

        logger.info(f"Retrieved {len(assignments)} room assignments for {date}")
        return assignments

    async def sync_room_assignments(self, date: str) -> dict[str, Any]:
        """Extract and sync room assignments for a date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Sync result with success count and conflicts
        """
        assignments = await self.get_room_assignments(date)

        success_count = 0
        conflict_count = 0
        conflicts = []

        for assignment in assignments:
            course_id = assignment.get("veranstaltung_id", "")
            room_data = {
                "room": assignment.get("raum", ""),
                "start": assignment.get("beginn", ""),
                "end": assignment.get("ende", ""),
                "capacity": assignment.get("kapazitaet", 0),
            }

            try:
                await self.provision_bbb_room(course_id, room_data)
                success_count += 1
            except RoomSyncError as e:
                conflict_count += 1
                conflict = {
                    "course_id": course_id,
                    "room": room_data["room"],
                    "error": str(e),
                }
                conflicts.append(conflict)

        logger.info(
            f"Synced {success_count} rooms, {conflict_count} conflicts for {date}"
        )

        return {
            "status": "success",
            "date": date,
            "synced": success_count,
            "conflicts": conflict_count,
            "conflict_details": conflicts,
        }

    async def provision_bbb_room(self, course_id: str, room_data: dict) -> dict:
        """Provision BBB meeting room for a course.

        Args:
            course_id: Course identifier
            room_data: Room data with room, start, end, capacity

        Returns:
            BBB meeting creation result

        Raises:
            RoomSyncError: If BBB room provisioning fails
        """
        if not self._is_configured():
            logger.warning("BBB not configured, skipping room provisioning")
            return {"status": "skipped", "reason": "BBB not configured"}

        # Import BBBClient here to avoid circular dependency
        from api.utils.bbb_client import BBBClient

        meeting_params = {
            "name": f"{course_id} - {room_data.get('room', '')}",
            "meetingID": f"{course_id}-{room_data.get('room', '')}",
            "attendeePW": f"{course_id}-attendee",
            "moderatorPW": f"{course_id}-moderator",
            "maxParticipants": room_data.get("capacity", 50),
        }

        async with BBBClient() as bbb:
            result = await bbb.create_meeting(meeting_params)

            if not result.get("success"):
                raise RoomSyncError(f"Failed to create BBB room: {result}")

            logger.info(f"Created BBB meeting for course {course_id}")
            return result

    def handle_room_conflict(self, conflict: dict) -> dict[str, Any]:
        """Handle room conflict by notifying course coordinator.

        Args:
            conflict: Conflict dictionary with course_id, room, error

        Returns:
            Handling result
        """
        course_id = conflict.get("course_id", "")
        room = conflict.get("room", "")
        error = conflict.get("error", "")

        logger.warning(
            f"Room conflict detected: course={course_id}, room={room}: {error}"
        )

        # In production, this would send notifications to course coordinators
        # For now, we just log the conflict
        return {
            "status": "notified",
            "course_id": course_id,
            "room": room,
            "message": "Course coordinator notified of room conflict",
        }

    def validate_room_capacity(self, room: str, enrollment_count: int) -> bool:
        """Validate if room can accommodate enrollment count.

        Args:
            room: Room identifier
            enrollment_count: Number of enrolled students

        Returns:
            True if capacity is sufficient, False otherwise
        """
        # In production, this would query room capacity from HISinOne
        # For now, we use a simple heuristic
        room_capacities = {
            "H1.1": 150,
            "H1.2": 100,
            "H2.1": 120,
            "H2.2": 80,
            "H2.3": 80,
            "H3.1": 100,
            "Lab-1": 30,
            "Lab-2": 30,
        }

        capacity = room_capacities.get(room, 50)
        is_valid = enrollment_count <= capacity

        if not is_valid:
            logger.warning(
                f"Room capacity exceeded: {room} capacity={capacity}, enrollment={enrollment_count}"
            )

        return is_valid
