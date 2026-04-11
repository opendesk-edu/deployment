# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
from typing import TYPE_CHECKING, Any, Optional
from datetime import datetime
import httpx
from api.config.settings import get_settings
from api.utils.hisinone_client import HISinOneClient
import logging

if TYPE_CHECKING:
    from api.utils.caldav_client import CalDAVClient

logger = logging.getLogger(__name__)


class ScheduleSyncError(Exception):
    """Exception raised for schedule sync errors."""

    pass


class ScheduleSyncEngine:
    """Schedule synchronization engine for HISinOne and CalDAV.

    Extracts schedules from HISinOne, generates ICS format, and syncs to CalDAV.
    Falls back to mock data when credentials are not configured.
    """

    def __init__(
        self,
        hisinone_client: Optional[HISinOneClient] = None,
    ):
        """Initialize schedule sync engine.

        Args:
            hisinone_client: Optional HISinOne client instance
        """
        settings = get_settings()
        self.hisinone_client = hisinone_client or HISinOneClient()
        self._caldav_client: Optional["CalDAVClient"] = None

    async def __aenter__(self) -> "ScheduleSyncEngine":
        """Initialize clients."""
        await self.hisinone_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close clients."""
        await self.hisinone_client.__aexit__(exc_type, exc_val, exc_tb)

    def _is_configured(self) -> bool:
        """Check if CalDAV is configured."""
        settings = get_settings()
        return bool(
            settings.caldav_url
            and settings.caldav_username
            and settings.caldav_password
        )

    async def get_schedule(self, user_id: str, semester: str) -> list[dict]:
        """Get schedule for a user from HISinOne.

        Args:
            user_id: User identifier
            semester: Semester code (e.g., "2026ws")

        Returns:
            List of schedule event dictionaries
        """
        # Call HISinOne SOAP getStundenplan
        schedule = await self.hisinone_client._soap_call(
            "getStundenplan",
            {"person_id": user_id, "semester": semester},
        )

        logger.info(f"Retrieved {len(schedule)} schedule events for {user_id}")
        return schedule

    async def sync_schedule_to_calendars(
        self, user_id: str, semester: str
    ) -> dict[str, Any]:
        """Extract schedule and sync to user's CalDAV calendar.

        Args:
            user_id: User identifier
            semester: Semester code

        Returns:
            Sync result with created/updated/deleted events count
        """
        if not self._is_configured():
            logger.warning("CalDAV not configured, skipping sync")
            return {
                "status": "skipped",
                "reason": "CalDAV not configured",
                "created": 0,
                "updated": 0,
                "deleted": 0,
            }

        # Import CalDAVClient here to avoid circular dependency
        from api.utils.caldav_client import CalDAVClient

        schedule = await self.get_schedule(user_id, semester)

        async with CalDAVClient() as caldav:
            calendar_path = f"/dav/{user_id}/calendar/"

            # Get existing events
            existing_events = await caldav.list_events(calendar_path)
            existing_uids = {event["uid"] for event in existing_events}

            created = 0
            updated = 0

            for event in schedule:
                event_uid = event.get("uid")
                ics_content = self.generate_ics(event)

                if not event_uid:
                    logger.warning(f"Skipping event with missing UID: {event}")
                    continue

                if event_uid in existing_uids:
                    # Update existing event
                    success = await caldav.update_event(
                        calendar_path, event_uid, ics_content
                    )
                    if success:
                        updated += 1
                else:
                    # Create new event
                    success = await caldav.create_event(
                        calendar_path, event_uid, ics_content
                    )
                    if success:
                        created += 1

            logger.info(f"Synced {created} new, {updated} updated events for {user_id}")

            return {
                "status": "success",
                "created": created,
                "updated": updated,
                "deleted": 0,
            }

    def generate_ics(self, event: dict) -> str:
        """Generate ICS format string from event data.

        Args:
            event: Event dictionary with title, start, end, room, recurrence

        Returns:
            ICS format string (VCALENDAR + VEVENT)
        """
        uid = event.get("uid", "")
        title = event.get("title", "Untitled Event")
        start = event.get("start", "")
        end = event.get("end", "")
        location = event.get("room", "")
        recurrence = event.get("recurrence", "")

        # Convert datetime to ICS format if needed
        if isinstance(start, datetime):
            start = start.strftime("%Y%m%dT%H%M%SZ")
        if isinstance(end, datetime):
            end = end.strftime("%Y%m%dT%H%M%SZ")

        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//openDesk Edu//Schedule Sync//EN
BEGIN:VEVENT
UID:{uid}
SUMMARY:{title}
DTSTART:{start}
DTEND:{end}
LOCATION:{location}
DTSTAMP:{datetime.now().strftime("%Y%m%dT%H%M%SZ")}"""

        if recurrence:
            ics += f"\nRRULE:{recurrence}"

        ics += "\nEND:VEVENT\nEND:VCALENDAR"

        return ics

    async def handle_schedule_change(self, event: dict) -> dict[str, Any]:
        """Detect schedule changes and return affected students.

        Args:
            event: Schedule change event data

        Returns:
            Dict with affected user_ids and change details
        """
        event_type = event.get("type", "unknown")
        course_id = event.get("course_id", "")
        event_id = event.get("event_id", "")

        logger.info(f"Handling schedule change: {event_type} for course {course_id}")

        # Get enrolled students for this course
        enrollments = await self.hisinone_client.get_enrollments(course_id)

        affected_user_ids = [enr["student_id"] for enr in enrollments]

        return {
            "event_type": event_type,
            "course_id": course_id,
            "event_id": event_id,
            "affected_user_ids": affected_user_ids,
            "user_count": len(affected_user_ids),
        }
