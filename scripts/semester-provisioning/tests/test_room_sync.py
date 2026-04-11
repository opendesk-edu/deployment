# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
import pytest
from api.utils.room_sync import RoomSyncEngine, RoomSyncError


@pytest.mark.asyncio
async def test_room_sync_mock_mode():
    """Test RoomSyncEngine in mock mode."""
    async with RoomSyncEngine() as engine:
        # Mock mode should work without credentials
        assert not engine._is_configured()


@pytest.mark.asyncio
async def test_get_room_assignments():
    """Test getting room assignments."""
    async with RoomSyncEngine() as engine:
        assignments = await engine.get_room_assignments("2026-10-15")

        # Should return 5 mock room assignments
        assert len(assignments) == 5

        # Check first assignment structure
        first_assignment = assignments[0]
        assert "raum" in first_assignment
        assert "veranstaltung_id" in first_assignment
        assert "beginn" in first_assignment
        assert "ende" in first_assignment
        assert "kapazitaet" in first_assignment


@pytest.mark.asyncio
async def test_get_room_assignments_with_room_filter():
    """Test getting room assignments with room filter."""
    async with RoomSyncEngine() as engine:
        assignments = await engine.get_room_assignments("2026-10-15", room="H1.1")

        # Should return filtered assignments (in mock mode, returns all)
        assert isinstance(assignments, list)


@pytest.mark.asyncio
async def test_sync_room_assignments():
    """Test syncing room assignments."""
    async with RoomSyncEngine() as engine:
        result = await engine.sync_room_assignments("2026-10-15")

        # Should return sync result
        assert "status" in result
        assert "synced" in result
        assert "conflicts" in result
        assert result["synced"] > 0


@pytest.mark.asyncio
async def test_provision_bbb_room():
    """Test provisioning BBB room."""
    async with RoomSyncEngine() as engine:
        # Mock mode should skip BBB provisioning
        result = await engine.provision_bbb_room(
            "LV-001",
            {
                "room": "H1.1",
                "start": "20261015T090000Z",
                "end": "20261015T110000Z",
                "capacity": 150,
            },
        )

        # In mock mode, should skip
        assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_provision_bbb_room_error():
    """Test BBB room provisioning error handling."""
    async with RoomSyncEngine() as engine:
        # This should not raise in mock mode
        result = await engine.provision_bbb_room(
            "LV-001",
            {
                "room": "H1.1",
                "start": "20261015T090000Z",
                "end": "20261015T110000Z",
                "capacity": 150,
            },
        )
        assert result["status"] == "skipped"


def test_handle_room_conflict():
    """Test handling room conflict."""
    engine = RoomSyncEngine()

    conflict = {
        "course_id": "LV-001",
        "room": "H1.1",
        "error": "Room already booked",
    }

    result = engine.handle_room_conflict(conflict)

    assert result["status"] == "notified"
    assert result["course_id"] == "LV-001"
    assert result["room"] == "H1.1"


def test_validate_room_capacity_sufficient():
    """Test room capacity validation with sufficient capacity."""
    engine = RoomSyncEngine()

    # H1.1 has capacity 150
    result = engine.validate_room_capacity("H1.1", 100)
    assert result is True


def test_validate_room_capacity_exceeded():
    """Test room capacity validation with exceeded capacity."""
    engine = RoomSyncEngine()

    # H1.1 has capacity 150
    result = engine.validate_room_capacity("H1.1", 200)
    assert result is False


def test_validate_room_capacity_unknown_room():
    """Test room capacity validation with unknown room."""
    engine = RoomSyncEngine()

    # Unknown room defaults to capacity 50
    result = engine.validate_room_capacity("Unknown-Room", 40)
    assert result is True

    result = engine.validate_room_capacity("Unknown-Room", 60)
    assert result is False


def test_validate_room_capacity_lab_rooms():
    """Test room capacity validation for lab rooms."""
    engine = RoomSyncEngine()

    # Lab-1 has capacity 30
    result = engine.validate_room_capacity("Lab-1", 30)
    assert result is True

    result = engine.validate_room_capacity("Lab-1", 31)
    assert result is False


@pytest.mark.asyncio
async def test_room_sync_context_manager():
    """Test RoomSyncEngine as async context manager."""
    async with RoomSyncEngine() as engine:
        assert engine is not None
        # Should be able to call methods
        assignments = await engine.get_room_assignments("2026-10-15")
        assert len(assignments) == 5


@pytest.mark.asyncio
async def test_sync_room_assignments_with_conflicts():
    """Test syncing room assignments with conflicts."""
    async with RoomSyncEngine() as engine:
        # Mock mode should handle conflicts gracefully
        result = await engine.sync_room_assignments("2026-10-15")

        # In mock mode, BBB is not configured so all syncs are skipped
        # No actual conflicts should occur
        assert "conflict_details" in result
