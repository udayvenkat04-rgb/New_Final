import pytest
from datetime import datetime
from models import User, MissingPerson, FaceVector, Sighting, MatchResult
from repositories import (
    UserRepository,
    CaseRepository,
    FaceRepository,
    SightingRepository,
    MatchRepository
)

@pytest.fixture(autouse=True)
def cleanup_database():
    """Fixture to clean up test data before and after tests."""
    user_repo = UserRepository()
    case_repo = CaseRepository()
    face_repo = FaceRepository()
    sighting_repo = SightingRepository()
    match_repo = MatchRepository()

    # Teardown logic
    def cleanup():
        user_repo.collection.delete_many({"email": {"$regex": "^repo_test_"}})
        case_repo.collection.delete_many({"contact_email": {"$regex": "^repo_test_"}})
        face_repo.collection.delete_many({"case_id": {"$in": [-100, -200, -300]}})
        sighting_repo.collection.delete_many({"video_path": {"$regex": "^repo_test_"}})
        match_repo.collection.delete_many({"case_id": {"$in": [-100, -200, -300]}})

    cleanup()
    yield
    cleanup()


def test_user_repository_crud():
    user_repo = UserRepository()

    # Create
    user = User(
        name="Repo Test User",
        email="repo_test_user@example.com",
        password_hash="hashed_pw",
        role="officer"
    )
    created = user_repo.create(user)
    assert created.id is not None
    assert created.name == "Repo Test User"

    # Find by ID
    fetched = user_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.email == "repo_test_user@example.com"
    assert fetched.is_active is True

    # Find by Email
    fetched_email = user_repo.get_by_email("repo_test_user@example.com")
    assert fetched_email is not None
    assert fetched_email.id == created.id

    # Update
    fetched.name = "Repo Test User Updated"
    updated = user_repo.update(fetched)
    assert updated.name == "Repo Test User Updated"

    # Deactivate
    deactivated = user_repo.deactivate(created.id)
    assert deactivated is True
    fetched_deactive = user_repo.get_by_id(created.id)
    assert fetched_deactive.is_active is False

    # Delete
    deleted = user_repo.delete(created.id)
    assert deleted is True
    assert user_repo.get_by_id(created.id) is None


def test_case_repository_crud():
    case_repo = CaseRepository()

    # Create
    case = MissingPerson(
        name="Repo Test Case",
        age=25,
        gender="Female",
        last_seen_location="Repo Test Location",
        last_seen_date=datetime.utcnow(),
        case_number="CASE-REPO-123",
        contact_name="Bob",
        contact_email="repo_test_bob@example.com",
        contact_phone="1234567890",
        last_seen_city="Repo City",
        last_seen_state="Repo State",
        status="Missing",
        created_by="repo_officer"
    )
    created = case_repo.create(case)
    assert created.id is not None
    assert created.case_number == "CASE-REPO-123"

    # Find by ID
    fetched = case_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Repo Test Case"

    # Find by Case Number
    fetched_cn = case_repo.get_by_case_number("CASE-REPO-123")
    assert fetched_cn is not None
    assert fetched_cn.id == created.id

    # Update
    fetched.name = "Repo Test Case Updated"
    updated = case_repo.update(fetched)
    assert updated.name == "Repo Test Case Updated"

    # List all
    all_cases = case_repo.list_all()
    assert len(all_cases) > 0
    assert any(c.id == created.id for c in all_cases)

    # Get by officer
    officer_cases = case_repo.get_by_officer("repo_officer")
    assert len(officer_cases) == 1
    assert officer_cases[0].id == created.id

    # Filter by status
    missing_cases = case_repo.filter_by_status("Missing")
    assert len(missing_cases) > 0

    # Filter by city/state
    location_cases = case_repo.filter_by_location(city="Repo City", state="Repo State")
    assert len(location_cases) == 1
    assert location_cases[0].id == created.id

    # Delete
    deleted = case_repo.delete(created.id)
    assert deleted is True
    assert case_repo.get_by_id(created.id) is None


def test_face_repository_crud():
    face_repo = FaceRepository()

    # Save Vector
    vector = FaceVector(
        vector=[0.1, 0.2, 0.3],
        case_id=-100
    )
    created = face_repo.save_vector(vector)
    assert created.id is not None
    assert created.dimensions == 3

    # Get Vector by Case
    case_vectors = face_repo.get_by_case(-100)
    assert len(case_vectors) == 1
    assert case_vectors[0].vector == [0.1, 0.2, 0.3]

    # List vectors
    all_vectors = face_repo.list_all()
    assert len(all_vectors) > 0
    assert any(v.id == created.id for v in all_vectors)

    # Delete by case
    deleted = face_repo.delete_by_case(-100)
    assert deleted is True
    assert len(face_repo.get_by_case(-100)) == 0


def test_sighting_repository_crud():
    sighting_repo = SightingRepository()

    # Create
    sighting = Sighting(
        case_id=-200,
        video_path="repo_test_video.mp4",
        frame_number=15,
        timestamp_seconds=2.5,
        location="Repo Intersection",
        status="Pending"
    )
    created = sighting_repo.create(sighting)
    assert created.id is not None
    assert created.video_path == "repo_test_video.mp4"

    # Find sightings
    sightings = sighting_repo.find_sightings({"video_path": "repo_test_video.mp4"})
    assert len(sightings) == 1
    assert sightings[0].id == created.id

    # Find by case
    case_sightings = sighting_repo.get_by_case(-200)
    assert len(case_sightings) == 1
    assert case_sightings[0].id == created.id

    # Delete
    deleted = sighting_repo.delete(created.id)
    assert deleted is True
    assert sighting_repo.get_by_id(created.id) is None


def test_match_repository_crud():
    match_repo = MatchRepository()

    # Create match result
    match = MatchResult(
        case_id=-300,
        sighting_id=5,
        similarity=0.88,
        status="Pending Review"
    )
    created = match_repo.create(match)
    assert created.id is not None
    assert created.similarity == 0.88

    # Find match
    fetched = match_repo.find_match(created.id)
    assert fetched is not None
    assert fetched.similarity == 0.88

    # Update status
    updated = match_repo.update_status(created.id, "Confirmed Match")
    assert updated is True
    fetched_updated = match_repo.find_match(created.id)
    assert fetched_updated.status == "Confirmed Match"

    # List potential matches
    # Since we changed status to Confirmed Match, let's create another one that's Pending Review
    pending_match = MatchResult(
        case_id=-300,
        sighting_id=6,
        similarity=0.92,
        status="Pending Review"
    )
    match_repo.create(pending_match)
    potentials = match_repo.list_potential_matches()
    assert len(potentials) > 0
    assert any(m.similarity == 0.92 for m in potentials)

    # List by case
    case_matches = match_repo.list_by_case(-300)
    assert len(case_matches) == 2

    # Delete by case
    deleted = match_repo.delete_by_case(-300)
    assert deleted is True
    assert len(match_repo.list_by_case(-300)) == 0
