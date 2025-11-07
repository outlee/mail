import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import RefreshToken, User, UserRole
from app.security import hash_password, verify_password


class UserService:
    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.OPERATOR,
    ) -> User:
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        db_user = User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> Optional[User]:
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


class RefreshTokenService:
    @staticmethod
    def create_refresh_token(
        db: Session, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token_id = str(uuid.uuid4())
        db_token = RefreshToken(
            id=token_id, user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        return db_token

    @staticmethod
    def get_refresh_token(
        db: Session, token_hash: str
    ) -> Optional[RefreshToken]:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

    @staticmethod
    def revoke_refresh_token(db: Session, token_id: str) -> bool:
        token = db.query(RefreshToken).filter(RefreshToken.id == token_id).first()
        if token:
            token.revoked = True
            db.commit()
            return True
        return False
