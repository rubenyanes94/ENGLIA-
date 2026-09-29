"""Primitivas de seguridad: hashing de contraseñas y JWT.

Deliberadamente sin importar nada de SQLAlchemy/FastAPI aquí — esta capa
no sabe qué es un "usuario" ni una request HTTP, solo sabe hashear texto
y firmar/verificar tokens. Quien conecta esto con la base de datos y con
FastAPI es app/core/deps.py.
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """`subject` es el id del usuario (como string). Va en el claim `sub`,
    el estándar de JWT para "de quién es este token"."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire, "purpose": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Devuelve el `sub` (id del usuario) si el token es válido.
    Lanza jwt.PyJWTError (expirado, firma inválida, etc.) si no lo es —
    quien llama decide cómo traducir eso a una respuesta HTTP."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    # Los tokens de otro propósito (el de baja de correos, que no caduca
    # nunca) se firman con la MISMA clave: sin esta comprobación, pegar el
    # enlace de un correo viejo en la cabecera Authorization sería una
    # sesión eterna. Los tokens emitidos antes de que existiera este claim
    # no lo traen y se siguen aceptando.
    if payload.get("purpose", "access") != "access":
        raise jwt.InvalidTokenError("Este token no sirve para iniciar sesión.")
    return payload["sub"]


def create_unsubscribe_token(subject: str) -> str:
    """Token del enlace "no quiero recibir estos recordatorios".

    Sin caducidad a propósito: el enlace tiene que seguir funcionando en
    un correo de hace ocho meses, que es justo cuando alguien lo busca.
    Va firmado para que nadie pueda dar de baja a otro cambiando un id en
    la URL, y con `purpose` para que no valga como sesión."""
    return jwt.encode({"sub": subject, "purpose": "unsubscribe"}, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_unsubscribe_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("purpose") != "unsubscribe":
        raise jwt.InvalidTokenError("Este token no sirve para darse de baja.")
    return payload["sub"]


def _password_fingerprint(hashed_password: str) -> str:
    """Huella de la contraseña ACTUAL, para atar a ella el enlace de
    restablecer. Un HMAC y no el hash tal cual: el JWT se lee sin la clave
    y no hay por qué regalar ni un trozo del bcrypt."""
    return hmac.new(settings.secret_key.encode(), hashed_password.encode(), hashlib.sha256).hexdigest()[:24]


def create_password_reset_token(subject: str, hashed_password: str) -> str:
    """Token del botón "Cambiar mi contraseña" del correo.

    Caduca pronto (PASSWORD_RESET_EXPIRE_MINUTES) y es de un solo uso sin
    guardar nada en la base de datos: lleva la huella de la contraseña con
    la que se emitió, y en cuanto se cambia la contraseña deja de coincidir.
    Eso invalida a la vez este enlace y cualquier otro que se haya pedido
    antes."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    payload = {"sub": subject, "exp": expire, "purpose": "password_reset", "pwd": _password_fingerprint(hashed_password)}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> tuple[str, str]:
    """Devuelve (id del usuario, huella). Quien llama compara la huella
    con `password_reset_matches` una vez cargado el usuario."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("purpose") != "password_reset" or "pwd" not in payload:
        raise jwt.InvalidTokenError("Este token no sirve para cambiar la contraseña.")
    return payload["sub"], payload["pwd"]


def password_reset_matches(fingerprint: str, hashed_password: str) -> bool:
    return hmac.compare_digest(fingerprint, _password_fingerprint(hashed_password))
