"""Da rol de gerencia ("manager") a una cuenta ya registrada.

Gerencia solo LEE el panel de analítica (routers/management.py): no puede
editar contenido, aprobar pagos ni ver /admin. Igual que con
promote_admin, no hay endpoint público para asignarse este rol.

Uso:
    python -m app.scripts.promote_manager correo@ejemplo.com
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import User


async def promote_manager(email: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalars().first()

        if user is None:
            print(f"No existe ninguna cuenta con el email '{email}'. Regístrala primero desde /auth/register.")
            return

        if user.role == "manager":
            print(f"'{email}' ya era de gerencia. Nada que hacer.")
            return

        if user.role == "admin":
            # Bajar a un admin a gerencia le quitaría permisos sin avisar;
            # si de verdad se quiere, que sea un cambio explícito a mano.
            print(f"'{email}' es admin, que ya ve el panel de gerencia. No se cambia.")
            return

        user.role = "manager"
        await session.commit()
        print(f"'{email}' ahora es de gerencia.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.scripts.promote_manager correo@ejemplo.com")
        sys.exit(1)

    asyncio.run(promote_manager(sys.argv[1]))
