from typing import ClassVar

from sqlmodel import Field, SQLModel


class TokenPayload(SQLModel):
    """Token payload model for JWT authentication."""

    sub: str | None = None


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__: ClassVar[str] = "user"  # type: ignore[misc]

    id: int | None = Field(default=None, primary_key=True)  # type: Any
    email: str = Field(unique=True, index=True, max_length=255)  # type: Any
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
