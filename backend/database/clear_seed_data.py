import os
import glob
from backend.database.connection import get_database, check_connection

def clear_seed_data():
    connected, msg = check_connection()
    if not connected:
        print(f"ERROR: Cannot connect to MongoDB. {msg}")
        return False
        
    db = get_database()
    
    # Collections to clear
    collections_to_clear = [
        "missing_persons",
        "face_vectors",
        "sightings",
        "match_results",
        "case_history"
    ]
    
    print("Clearing collections from MongoDB...")
    for coll_name in collections_to_clear:
        result = db[coll_name].delete_many({})
        print(f"Cleared collection '{coll_name}': deleted {result.deleted_count} documents.")
        
    # Clear uploaded images in data/uploads/
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
    print(f"Cleaning upload directory: {upload_dir}...")
    if os.path.exists(upload_dir):
        extensions = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
        deleted_files_count = 0
        for ext in extensions:
            files = glob.glob(os.path.join(upload_dir, ext))
            for file_path in files:
                try:
                    os.remove(file_path)
                    deleted_files_count += 1
                except Exception as e:
                    print(f"Failed to delete file {file_path}: {e}")
        print(f"Deleted {deleted_files_count} uploaded image files.")
        
    print("\nSUCCESS: All seeded cases, sightings, face vectors, matches, and history have been removed successfully!")
    print("Your users collection remains intact so you can still log in and register your own data.")
    return True

if __name__ == "__main__":
    clear_seed_data()
