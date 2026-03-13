
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models.auth_models import User, CitizenProfile

def check_profiles():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"User ID: {u.id}, Email: {u.email}")
            profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == u.id).first()
            if profile:
                print(f"  Profile Found: Employment={profile.employment_type}, Senior={profile.senior_citizen}")
            else:
                print(f"  No Profile Found for this user.")
    finally:
        db.close()

if __name__ == "__main__":
    check_profiles()
