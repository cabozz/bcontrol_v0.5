import asyncio
import getpass

from app.db import init_db_pool, get_pool
from app.auth_session import hash_password


async def main():
    # ensure DB pool/tables are ready
    await init_db_pool()
    pool = get_pool()

    username = input("Username: ").strip()
    password = getpass.getpass("Password (hidden): ").strip()
    role = input("Role (admin/operator): ").strip().lower()

    if role not in ("admin", "operator"):
        print("Role must be 'admin' or 'operator'")
        return

    pw_hash = hash_password(password)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES ($1, $2, $3);
            """,
            username, pw_hash, role
        )

    print(f"✅ Created user '{username}' with role '{role}'")


if __name__ == "__main__":
    asyncio.run(main())
