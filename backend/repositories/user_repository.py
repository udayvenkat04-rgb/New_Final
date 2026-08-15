from backend.database import get_database
from backend.models import User

class UserRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.users

    def create(self, user: User) -> User:
        max_doc = self.collection.find_one(sort=[("id", -1)])
        next_id = (max_doc.get("id") + 1) if max_doc else 1
        user.id = next_id
        self.collection.insert_one(user.to_dict())
        return user

    def get_by_id(self, user_id: int) -> User:
        data = self.collection.find_one({"id": user_id})
        return User.from_dict(data) if data else None

    def get_by_username(self, username: str) -> User:
        import re
        clean_user = username.strip()
        data = self.collection.find_one({
            "$or": [
                {"username": {"$regex": f"^{re.escape(clean_user)}$", "$options": "i"}},
                {"name": {"$regex": f"^{re.escape(clean_user)}$", "$options": "i"}},
                {"role": {"$regex": f"^{re.escape(clean_user)}$", "$options": "i"}}
            ]
        })
        return User.from_dict(data) if data else None

    def get_by_email(self, email: str) -> User:
        import re
        clean_email = email.strip()
        data = self.collection.find_one({"email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"}})
        return User.from_dict(data) if data else None

    def update(self, user: User) -> User:
        self.collection.replace_one({"id": user.id}, user.to_dict())
        return user

    def deactivate(self, user_id: int) -> bool:
        res = self.collection.update_one({"id": user_id}, {"$set": {"is_active": False}})
        return res.modified_count > 0

    def delete(self, user_id: int) -> bool:
        res = self.collection.delete_one({"id": user_id})
        return res.deleted_count > 0

    def get_all(self):
        docs = self.collection.find()
        return [User.from_dict(doc) for doc in docs]

