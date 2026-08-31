"""Da rol admin a una cuenta ya registrada — es la única forma de crear
el primer administrador (no hay un endpoint público para auto-asignarse
admin, por razones obvias).

Uso:
    python -m app.scripts.promote_admin correo@ejemplo.com
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import User


async def promote_admin(email: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalars().first()

        if user is None:
            print(f"No existe ninguna cuenta con el email '{email}'. Regístrala primero desde /auth/register.")
            return

        if user.role == "admin":
            print(f"'{email}' ya era admin. Nada que hacer.")
            return

        user.role = "admin"
        await session.commit()
        print(f"'{email}' ahora es admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.scripts.promote_admin correo@ejemplo.com")
        sys.exit(1)

    asyncio.run(promote_admin(sys.argv[1]))
