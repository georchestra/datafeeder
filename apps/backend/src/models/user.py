from sqlmodel import Field, SQLModel


class TokenPayload(SQLModel):
    """Token payload model for JWT authentication."""

    sub: str | None = None


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
