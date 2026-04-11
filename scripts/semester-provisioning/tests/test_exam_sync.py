# SPDX-FileCopyrightText: 2024 Zentrum für Digitale Souveränität der öffentlichen Verwaltung (ZenDiS) GmbH
# SPDX-FileCopyrightText: 2024 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
# SPDX-License-Identifier: Apache-2.0
import pytest
from api.utils.exam_sync import ExamSyncEngine, ExamSyncError
from api.utils.hisinone_client import HISinOneClient


@pytest.fixture
def exam_sync_engine():
    """Create an exam sync engine instance for testing."""
    return ExamSyncEngine()


@pytest.fixture
def mock_hisinone_client():
    """Create a mock HISinOne client for testing."""
    return HISinOneClient()


class TestExamSyncEngine:
    """Test cases for ExamSyncEngine class."""

    @pytest.mark.asyncio
    async def test_exam_sync_engine_initialization(self, exam_sync_engine):
        """Test that exam sync engine initializes correctly."""
        assert exam_sync_engine is not None
        assert exam_sync_engine.hisinone_client is not None

    @pytest.mark.asyncio
    async def test_exam_sync_engine_is_configured_false(self, exam_sync_engine):
        """Test that _is_configured returns False when OpenCloud not configured."""
        assert exam_sync_engine._is_configured() is False

    @pytest.mark.asyncio
    async def test_get_exams_returns_mock_data(self, exam_sync_engine):
        """Test that get_exams returns mock exam data when not configured."""
        async with exam_sync_engine:
            exams = await exam_sync_engine.get_exams(semester="2026ws")
            assert len(exams) == 5
            assert exams[0]["id"] == "EXM-001"
            assert exams[0]["courseId"] == "LV-001"

    @pytest.mark.asyncio
    async def test_get_exams_with_course_filter(self, exam_sync_engine):
        """Test that get_exams filters by course_id when provided."""
        async with exam_sync_engine:
            exams = await exam_sync_engine.get_exams(
                semester="2026ws", course_id="LV-001"
            )
            assert len(exams) == 3
            assert all(exam["courseId"] == "LV-001" for exam in exams)

    @pytest.mark.asyncio
    async def test_get_exams_with_invalid_course(self, exam_sync_engine):
        """Test that get_exams returns empty list for non-existent course."""
        async with exam_sync_engine:
            exams = await exam_sync_engine.get_exams(
                semester="2026ws", course_id="INVALID"
            )
            assert len(exams) == 0

    @pytest.mark.asyncio
    async def test_create_exam_in_lms_ilias(self, exam_sync_engine):
        """Test creating exam event in ILIAS."""
        exam = {
            "id": "EXM-001",
            "title": "Test Exam",
            "beginn": "20270120T090000Z",
            "ende": "20270120T120000Z",
        }
        lms_type = "ilias"
        lms_course_id = "ilias_123"

        async with exam_sync_engine:
            result = await exam_sync_engine.create_exam_in_lms(
                exam, lms_type, lms_course_id
            )
            assert "exam_event_id" in result
            assert "status" in result

    @pytest.mark.asyncio
    async def test_create_exam_in_lms_moodle(self, exam_sync_engine):
        """Test creating exam event in Moodle."""
        exam = {
            "id": "EXM-002",
            "title": "Test Exam",
            "beginn": "20270121T090000Z",
            "ende": "20270121T120000Z",
        }
        lms_type = "moodle"
        lms_course_id = "mdl_456"

        async with exam_sync_engine:
            result = await exam_sync_engine.create_exam_in_lms(
                exam, lms_type, lms_course_id
            )
            assert "grade_item_id" in result
            assert "status" in result

    @pytest.mark.asyncio
    async def test_sync_seating_plan_mock_mode(self, exam_sync_engine):
        """Test that sync_seating_plan works in mock mode."""
        exam_id = "EXM-001"
        seating_data = {"seat_1": "student-001", "seat_2": "student-002"}

        async with exam_sync_engine:
            result = await exam_sync_engine.sync_seating_plan(exam_id, seating_data)
            assert result["status"] == "uploaded"
            assert result["exam_id"] == exam_id

    @pytest.mark.asyncio
    async def test_sync_seating_plan_uses_correct_path(self, exam_sync_engine):
        """Test that sync_seating_plan uses correct OpenCloud path."""
        exam_id = "EXM-002"
        seating_data = {"seat_1": "student-001"}

        async with exam_sync_engine:
            result = await exam_sync_engine.sync_seating_plan(exam_id, seating_data)
            assert "path" in result
            assert "EXM-002" in result["path"]
            assert "seating-plan.pdf" in result["path"]

    @pytest.mark.asyncio
    async def test_get_exam_participants_mock_mode(self, exam_sync_engine):
        """Test that get_exam_participants returns mock data."""
        exam_id = "EXM-001"

        async with exam_sync_engine:
            participants = await exam_sync_engine.get_exam_participants(exam_id)
            assert len(participants) > 0
            assert "student_id" in participants[0]

    @pytest.mark.asyncio
    async def test_sync_exam_schedule_full_workflow(self, exam_sync_engine):
        """Test full exam schedule sync workflow."""
        async with exam_sync_engine:
            result = await exam_sync_engine.sync_exam_schedule(semester="2026ws")
            assert result["status"] == "success"
            assert "synced" in result
            assert result["synced"] > 0

    @pytest.mark.asyncio
    async def test_sync_exam_schedule_with_course_filter(self, exam_sync_engine):
        """Test exam schedule sync with course filter."""
        async with exam_sync_engine:
            result = await exam_sync_engine.sync_exam_schedule(
                semester="2026ws", course_id="LV-001"
            )
            assert result["status"] == "success"
            assert result["synced"] > 0

    @pytest.mark.asyncio
    async def test_create_exam_in_lms_invalid_lms_type(self, exam_sync_engine):
        """Test that create_exam_in_lms raises error for invalid LMS type."""
        exam = {"id": "EXM-001", "title": "Test Exam"}
        lms_type = "invalid"
        lms_course_id = "course_123"

        async with exam_sync_engine:
            with pytest.raises(ExamSyncError) as exc_info:
                await exam_sync_engine.create_exam_in_lms(exam, lms_type, lms_course_id)
            assert "Unsupported LMS type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sync_exam_schedule_handles_errors_gracefully(self, exam_sync_engine):
        """Test that sync_exam_schedule handles errors and continues."""
        async with exam_sync_engine:
            result = await exam_sync_engine.sync_exam_schedule(semester="2026ws")
            assert result["status"] in ["success", "partial"]
            assert "synced" in result
            assert "errors" in result

    @pytest.mark.asyncio
    async def test_context_manager_initializes_clients(self, exam_sync_engine):
        """Test that async context manager initializes clients."""
        async with exam_sync_engine:
            assert exam_sync_engine.hisinone_client is not None
            # Should be able to call methods
            exams = await exam_sync_engine.get_exams(semester="2026ws")
            assert len(exams) == 5

    @pytest.mark.asyncio
    async def test_context_manager_closes_clients(self, exam_sync_engine):
        """Test that async context manager closes clients gracefully."""
        async with exam_sync_engine:
            # Context manager should be usable
            exams = await exam_sync_engine.get_exams(semester="2026ws")
            assert len(exams) > 0
        # After context manager exits, the engine can be used again
        # (it will reinitialize the clients)
        async with exam_sync_engine:
            exams = await exam_sync_engine.get_exams(semester="2026ws")
            assert len(exams) > 0


class TestExamSyncError:
    """Test cases for ExamSyncError exception."""

    def test_exam_sync_error_is_exception(self):
        """Test that ExamSyncError is an exception."""
        error = ExamSyncError("Test error message")
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"
