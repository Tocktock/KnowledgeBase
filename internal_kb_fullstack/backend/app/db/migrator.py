from __future__ import annotations

from pathlib import Path

import psycopg

from app.core.config import get_settings

SQL_DIR = Path(__file__).resolve().parent / "sql"


def render_template(text: str, *, embedding_dimensions: int) -> str:
    return text.replace("__EMBEDDING_DIMENSIONS__", str(embedding_dimensions))


def main() -> None:
    settings = get_settings()
    sql_files = sorted(SQL_DIR.glob("*.sql"))

    with psycopg.connect(settings.sync_database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version text PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            conn.commit()

            for sql_file in sql_files:
                version = sql_file.stem
                cur.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
                if cur.fetchone():
                    continue

                statement = render_template(
                    sql_file.read_text(encoding="utf-8"),
                    embedding_dimensions=settings.embedding_dimensions,
                )
                cur.execute(statement)
                cur.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (version,))
                conn.commit()
                print(f"Applied migration {version}")


if __name__ == "__main__":
    main()
