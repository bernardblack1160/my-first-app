import os

from sqlalchemy import select

from .auth import hash_password, normalize_email
from .db import SessionLocal
from .models import Membership, User, Workspace


def env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def get_or_create_user(db, email: str, display_name: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, display_name=display_name, password_hash=hash_password(password))
        db.add(user)
        db.flush()
    else:
        user.display_name = display_name
    return user


def main() -> None:
    workspace_name = env("LILA_WORKSPACE_NAME", "ملک من")
    manager_email = normalize_email(env("LILA_MANAGER_EMAIL", "manager@example.com"))
    manager_password = env("LILA_MANAGER_PASSWORD", "change-me-now")
    manager_name = env("LILA_MANAGER_NAME", "مدیر")
    owner_email = normalize_email(env("LILA_OWNER_EMAIL", "owner@example.com"))
    owner_password = env("LILA_OWNER_PASSWORD", "change-me-now")
    owner_name = env("LILA_OWNER_NAME", "مالک")
    if len(manager_password) < 8 or len(owner_password) < 8:
        raise SystemExit("Seed passwords must contain at least 8 characters")

    with SessionLocal() as db:
        workspace = db.scalar(select(Workspace).where(Workspace.name == workspace_name))
        if not workspace:
            workspace = Workspace(name=workspace_name)
            db.add(workspace)
            db.flush()
        manager = get_or_create_user(db, manager_email, manager_name, manager_password)
        owner = get_or_create_user(db, owner_email, owner_name, owner_password)
        for user, role in ((manager, "manager"), (owner, "owner")):
            membership = db.scalar(select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id))
            if membership:
                membership.role = role
            else:
                db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=role))
        db.commit()
    print(f"Workspace ready: {workspace_name}")


if __name__ == "__main__":
    main()
