from sqlalchemy.orm import Session
from .models import User
from .auth import get_password_hash

def seed_initial_data(db: Session = None):
    pass

def seed_db():
    pass

if __name__ == "__main__":
    seed_db()
