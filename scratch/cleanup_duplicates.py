import sys
import os
from backend.repositories.case_repository import CaseRepository

def cleanup():
    repo = CaseRepository()
    cases = repo.get_all(include_deleted=False)
    print(f"Total active cases found: {len(cases)}")
    
    seen = {}
    deleted_count = 0
    for c in cases:
        key = (c.name.strip().lower(), c.age, (c.last_seen_location or "").strip().lower())
        if key in seen:
            # Duplicate found! Delete it from database.
            repo.hard_delete(c.id) if hasattr(repo, "hard_delete") else repo.delete(c.id)
            print(f"Removed duplicate case {c.case_number} (id: {c.id}) for {c.name}")
            deleted_count += 1
        else:
            seen[key] = c
            
    print(f"Cleanup complete. Removed {deleted_count} duplicate cases. {len(seen)} unique cases remaining.")

if __name__ == "__main__":
    cleanup()
