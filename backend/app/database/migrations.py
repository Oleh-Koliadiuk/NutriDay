from sqlalchemy import inspect, text

from .session import engine


def apply_schema_migrations() -> None:
    """Apply small forward-compatible schema changes for existing SQLite databases."""
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        if "email" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(254)"))
        if "password_changed_at" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
