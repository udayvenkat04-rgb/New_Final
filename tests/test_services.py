import pytest
from datetime import datetime
from services.auth_service import AuthService
from services.case_service import CaseService
from services.match_review import MatchReviewService
from repositories import UserRepository, CaseRepository, SightingRepository, MatchRepository
from models import User, MissingPerson, Sighting, MatchResult

def test_auth_service_registration_and_login():
    user_repo = UserRepository()
    auth_service = AuthService(user_repo)
    
    # Delete test user if exists
    existing = user_repo.get_by_username("test_auth_service_user")
    if existing:
        user_repo.delete(existing.id)
    existing_email = user_repo.get_by_email("test_auth_service@example.com")
    if existing_email:
        user_repo.delete(existing_email.id)
        
    # Register user
    registered = auth_service.register_user(
        name="test_auth_service_user",
        email="test_auth_service@example.com",
        password="password123",
        role="officer"
    )
    
    assert registered.id is not None
    assert registered.id is not None
    assert registered.name == "test_auth_service_user"
    assert registered.email == "test_auth_service@example.com"
    assert registered.role == "officer"
    
    # Test duplicate check
    with pytest.raises(ValueError, match="already exists"):
        auth_service.register_user(
            name="test_auth_service_user",
            email="test_auth_service@example.com",
            password="password",
            role="officer"
        )
        
    # Authenticate user
    logged_in = auth_service.authenticate("test_auth_service@example.com", "password123")
    assert logged_in is not None
    assert logged_in.id == registered.id
    
    # Authenticate wrong password
    assert auth_service.authenticate("test_auth_service@example.com", "wrong_password") is None
    
    # Cleanup
    user_repo.delete(registered.id)

def test_case_service_registration():
    case_repo = CaseRepository()
    case_service = CaseService(case_repo)
    
    # Clean test cases
    existing = case_repo.get_all({"name": "Test Service Person"})
    for c in existing:
        case_repo.delete(c.id)
        
    registered = case_service.register_case(
        name="Test Service Person",
        age=30,
        gender="Male",
        last_seen_location="Test Location",
        contact_number="9999999999",
        description="Test descriptors",
        photo_path="data/faces/placeholder.png",
        reporter_name="Reporter Bob",
        reporter_contact="8888888888",
        last_seen_date=datetime.utcnow(),
        created_by="test_admin"
    )
    
    assert registered.id is not None
    assert registered.name == "Test Service Person"
    assert registered.status == "Missing"
    
    # Update status
    success = case_service.update_case_status(registered.id, "Found", updated_by="test_admin")
    assert success is True
    
    updated = case_repo.get_by_id(registered.id)
    assert updated.status == "Found"
    
    # Verify case timeline history logs
    logs = case_repo.get_history_by_case(registered.id)
    assert len(logs) >= 2
    actions = [l.action for l in logs]
    assert "Case Created" in actions
    assert "Status Changed" in actions
    
    # Cleanup
    case_repo.delete(registered.id)

def test_match_review_service():
    case_repo = CaseRepository()
    match_repo = MatchRepository()
    sighting_repo = SightingRepository()
    review_service = MatchReviewService(match_repo, case_repo)
    
    # Insert test case
    case = case_repo.create(MissingPerson(
        name="Match Review Target",
        age=40,
        gender="Female",
        last_seen_location="City Centre",
        contact_number="1111111111",
        description="Match test",
        photo_path="data/faces/placeholder2.png",
        status="Missing"
    ))
    
    # Insert test sighting
    sighting = sighting_repo.create(Sighting(
        case_id=case.id,
        photo_path="data/uploads/placeholder3.png",
        latitude=28.6139,
        longitude=77.2090,
        address="Central Station",
        reporter_name="Reporter Dave",
        reporter_contact="2222222222",
        details="Match sighting",
        status="Pending"
    ))
    
    # Insert test match result
    match_res = match_repo.create(MatchResult(
        case_id=case.id,
        sighting_id=sighting.id,
        confidence=0.85,
        status="Pending Review"
    ))
    
    assert match_res.id is not None
    
    # Review Match as Confirmed Match
    success = review_service.review_match(match_res.id, "Confirmed Match", reviewed_by="officer_joe")
    assert success is True
    
    # Verify case status automatically overridden to Found
    updated_case = case_repo.get_by_id(case.id)
    assert updated_case.status == "Found"
    
    # Verify match status updated
    updated_match = match_repo.get_by_id(match_res.id)
    assert updated_match.status == "Confirmed Match"
    
    # Cleanup
    case_repo.delete(case.id)
    sighting_repo.delete(sighting.id)
    match_repo.collection.delete_one({"id": match_res.id})
