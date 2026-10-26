import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv


BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))


def create_access_token(user_id):
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(int(user_id)),
        "iat": now,
        "exp": now + timedelta(hours=12),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def get_user_id_from_token(token):
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret or not token:
        return None

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )

        user_id = int(payload["sub"])
        return user_id if user_id > 0 else None

    except (jwt.InvalidTokenError, TypeError, ValueError, KeyError):
        return None
