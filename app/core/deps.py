from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _decode_token(token: str, verify_exp: bool = True) -> Optional[str]:
    """
    Decode a JWT and return the email subject, or None on any failure.
    Never raises — all exceptions are swallowed and returned as None
    so callers always get a clean 401, never a 500.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": verify_exp},
        )
        return payload.get("sub")
    except JWTError:
        # Catches ExpiredSignatureError, DecodeError, and everything else
        # python-jose can raise — all map to "invalid token → 401".
        return None
    except Exception:
        return None


async def _fetch_user(email: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


_CREDS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

_REFRESH_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token is invalid or too old to refresh",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Standard auth — expired tokens get a clean 401."""
    email = _decode_token(token, verify_exp=True)
    if not email:
        raise _CREDS_EXC
    user = await _fetch_user(email, db)
    if not user:
        raise _CREDS_EXC
    return user


async def get_current_user_lenient(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Used only by /refresh. Accepts expired tokens so the Flutter client
    can silently swap them without a login screen.
    verify_exp=False — python-jose still validates the signature,
    algorithm, and all other claims; only expiry is skipped.
    """
    email = _decode_token(token, verify_exp=False)
    if not email:
        raise _REFRESH_EXC
    user = await _fetch_user(email, db)
    if not user:
        raise _REFRESH_EXC
    return user