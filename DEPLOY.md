# Poner Espikin en línea (Railway + espikin.academy)

Guía para desplegar desde cero. Sigue los pasos en orden: cada uno
necesita algo del anterior.

## Qué vas a montar

```
                  espikin.academy
                         │
                         ▼
          ┌──────────────────────────┐
          │  frontend  (Caddy)       │   el build de React
          │  /api/*  ───────────────────┐
          └──────────────────────────┘  │ red privada de Railway
                                        ▼
                         ┌──────────────────────────┐
                         │  backend  (FastAPI)      │
                         └────────┬────────┬────────┘
                                  │        │
                    ┌─────────────┘        └──────────────┐
                    ▼                                     ▼
           ┌────────────────┐                    ┌────────────────┐
           │ Postgres       │                    │ Redis          │
           │ (con pgvector) │                    └───────┬────────┘
           └────────────────┘                            │
                                              ┌──────────┴─────────┐
                                              │ worker  (Celery)   │
                                              └────────────────────┘
```

Cinco servicios en un mismo proyecto de Railway. **El backend no necesita
dominio propio**: solo lo llama el frontend, por la red privada. Un
servicio menos expuesto a internet.

Por qué el frontend hace de proxy en vez de que el navegador llame a la
API directamente: así todo vive en un mismo origen. No hay CORS que
configurar, las fotos de perfil y los audios de las lecciones (que
cuelgan de `/api/media/...`) funcionan sin tocar nada, y los enlaces de
"darse de baja" que ya salieron en correos enviados —
`espikin.academy/api/notifications/baja` — siguen siendo válidos.

## Antes de empezar

Ten a mano:

- La clave de **NVIDIA** (el tutor) y la de **Resend** (los correos).
- Los datos de **Pago Móvil** y **Binance** que hoy están en tu `.env`.
- Una **SECRET_KEY nueva**. Genérala ahora y guárdala:
  ```bash
  openssl rand -hex 32
  ```
  No reutilices la de desarrollo. Con ella se firman las sesiones: quien
  la tenga puede entrar como cualquier cliente.

---

## Paso 1 · Postgres con pgvector

En Railway: **New → Template → busca "pgvector"** y despliégala.

**No uses el Postgres normal de Railway.** La memoria del tutor se guarda
en una columna de tipo `vector`, y sin esa extensión el backend no
levanta.

No hace falta que entres a la consola SQL a activar nada: las migraciones
crean la extensión solas al arrancar.

Cuando termine, renombra el servicio a **`Postgres`** (Settings → Name).
Los nombres se usan tal cual en el paso 3.

## Paso 2 · Redis

**New → Database → Add Redis.** Renómbralo a **`Redis`**.

## Paso 3 · Backend

1. **New → GitHub Repo → ENGLIA-**.
2. Settings → **Root Directory**: `backend`
3. Settings → **Healthcheck Path**: `/health`
4. Settings → **Volume**: añade uno montado en **`/app/media`**.
   Ahí van los audios de las lecciones y las fotos de perfil. Sin
   volumen, el disco del contenedor se borra en cada despliegue y los
   alumnos ven fotos rotas.
5. Renombra el servicio a **`backend`** (en minúscula: ese nombre lo usa
   el frontend para encontrarlo).
6. Variables (Settings → Variables → RAW Editor, pegar de una vez):

```bash
PORT=8000
ENVIRONMENT=production
SECRET_KEY=pega-aquí-lo-que-generaste
FRONTEND_BASE_URL=https://espikin.academy

DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}
REDIS_URL=redis://default:${{Redis.REDIS_PASSWORD}}@${{Redis.RAILWAY_PRIVATE_DOMAIN}}:6379/0
CELERY_BROKER_URL=redis://default:${{Redis.REDIS_PASSWORD}}@${{Redis.RAILWAY_PRIVATE_DOMAIN}}:6379/1

LLM_API_KEY=tu-clave-de-nvidia
EMBEDDING_API_KEY=tu-clave-de-nvidia
NVIDIA_API_KEY=tu-clave-de-nvidia

RESEND_API_KEY=tu-clave-de-resend
EMAIL_FROM=Espikin <onboarding@resend.dev>
EMAIL_REPLY_TO=gerencia.espikin@gmail.com
EMAIL_SANDBOX_TO=rubenyanes94@gmail.com

PAGO_MOVIL_BANK=...
PAGO_MOVIL_DOCUMENT=...
PAGO_MOVIL_PHONE=...
BINANCE_PERSONAL_QR_URL=...
BINANCE_PERSONAL_EMAIL=...
```

> **`DATABASE_URL` se arma a mano, no se copia.** Railway publica la suya
> como `postgresql://...` y aquí hace falta `postgresql+asyncpg://...`:
> es el driver asíncrono que usa la app. Con la de Railway tal cual, no
> arranca.

> **`EMAIL_FROM` y `EMAIL_SANDBOX_TO` se quedan como están hasta el paso
> 6.** Mientras el dominio no esté verificado en Resend, los correos solo
> pueden llegarte a ti, y es mejor que se desvíen a tu bandeja que que
> fallen en silencio.

> **No pongas `ENVIRONMENT=development`.** Eso deja visible el botón
> "Reportar pago" que activa la suscripción sin pagar.

## Paso 4 · Worker

Es el mismo repo otra vez, con un papel distinto.

1. **New → GitHub Repo → ENGLIA-** (sí, de nuevo).
2. Root Directory: `backend`
3. Renómbralo a **`worker`**.
4. **Sin healthcheck, sin volumen y sin dominio**: no atiende peticiones.
5. Variables: **las mismas del backend**, más:

```bash
ROLE=worker
```

`ROLE` es lo que decide si el contenedor arranca la API o el worker (ver
`backend/start.sh`). Y las migraciones solo las corre el backend, para
que dos despliegues simultáneos no se pisen a mitad de un `ALTER TABLE`.

## Paso 5 · Frontend

1. **New → GitHub Repo → ENGLIA-** (la tercera).
2. Root Directory: `frontend`
3. Renómbralo a **`frontend`**.
4. Variables:

```bash
BACKEND_HOST=backend.railway.internal:8000
```

Eso es todo: el frontend no lleva claves. Si renombraste el backend a
algo distinto de `backend`, cámbialo aquí también.

5. Settings → Networking → **Generate Domain**. Te da una URL
   `*.up.railway.app` para probar antes de tocar el dominio.

**Pruébalo ya**: abre esa URL. Debería cargar la portada, y
`<esa-url>/api/health` debería responder
`{"status":"ok","postgres":"connected","redis":"connected"}`.

Si el `/api/health` falla, el problema está entre frontend y backend:
revisa que el backend se llame exactamente `backend` y que tenga
`PORT=8000`.

## Paso 6 · El dominio

### En Railway

Servicio `frontend` → Settings → Networking → **Custom Domain** →
`espikin.academy`. Railway te da un destino tipo `xxxx.up.railway.app`.
Repítelo con `www.espikin.academy`.

### En Namecheap

Domain List → espikin.academy → **Advanced DNS**:

1. **Borra la regla de REDIRECT DOMAIN** que tienes
   (`espikin.academy → http://www.espikin.academy/`). Ahora la app vive
   en el dominio raíz y ese redirect se pelearía con ella.
2. Añade:

| Tipo | Host | Valor |
|---|---|---|
| ALIAS Record | `@` | el destino que te dio Railway |
| CNAME Record | `www` | el destino que te dio Railway |

El `@` va como **ALIAS** y no como CNAME: el estándar de DNS no permite
un CNAME en la raíz de un dominio. Namecheap tiene ALIAS justo para eso.

Tarda entre minutos y un par de horas. Railway te marca el dominio en
verde cuando lo ve y emite el certificado solo.

## Paso 7 · Correos con tu dominio

En [resend.com/domains](https://resend.com/domains) → **Add Domain** →
`espikin.academy`. Resend te da unos registros DNS (SPF, DKIM, DMARC):
cópialos a Namecheap → Advanced DNS igual que los anteriores.

Cuando Resend marque el dominio como verificado, en el servicio
**backend** cambia:

```bash
EMAIL_FROM=Espikin <hola@espikin.academy>
EMAIL_SANDBOX_TO=
```

`EMAIL_SANDBOX_TO` **vacío**. Mientras tenga algo, ningún correo llega a
los clientes: todos se desvían a esa dirección. El panel de gerencia →
Sistema te lo avisa en ámbar mientras siga puesto.

## Paso 8 · Llenar la base

La base nueva está vacía: no hay niveles, ni tutores, ni planes, ni
contenido. Abre una terminal del servicio **backend** en Railway
(⋮ → Shell, o `railway run` con su CLI) y ejecuta en este orden:

```bash
python -m app.scripts.seed_cefr_levels     # los 6 niveles del MCER
python -m app.scripts.seed_agent_personas  # un tutor por nivel
python -m app.scripts.seed_plans           # el plan de $10/mes
python -m app.scripts.seed_a1_modules      # el currículo de A1
python -m app.scripts.seed_a1_descriptors  # los descriptores de A1
python -m app.scripts.seed_module_exams    # los exámenes de cada módulo
python -m app.scripts.seed_library         # los cursos de la biblioteca
```

Todos son idempotentes: si los repites, no duplican nada.

Y el último, aparte porque **tarda** (genera y narra una lección por
módulo con el modelo y el sintetizador de voz, varios minutos):

```bash
python -m app.scripts.seed_a1_lessons
```

### Tu cuenta de gerencia

1. Regístrate en `https://espikin.academy` con `gerencia.espikin@gmail.com`.
2. En la terminal del backend:
   ```bash
   python -m app.scripts.promote_manager gerencia.espikin@gmail.com
   ```
3. Vuelve a entrar: ahora caes en el panel de gerencia.

Lo mismo con `promote_admin` para una cuenta de administración de
contenido, si la quieres.

## Paso 9 · Comprobar que todo está vivo

Entra a **gerencia → Sistema**. Esa pantalla existe para esto. Deberías
ver todo en verde salvo, como mucho, dos avisos:

- **"Modo de prueba de pagos"** → te falta `ENVIRONMENT=production`.
- **"Correos (Resend)"** en ámbar → o falta la clave, o
  `EMAIL_SANDBOX_TO` sigue puesta.

Y la lista a mano:

- [ ] `https://espikin.academy` carga y entra un usuario nuevo
- [ ] El chat del tutor responde (eso prueba NVIDIA)
- [ ] Llega el correo de bienvenida
- [ ] Una lección reproduce su audio (eso prueba el volumen)
- [ ] Subir una foto de perfil y recargar: sigue ahí
- [ ] gerencia → Pagos y gerencia → Correos cargan sin error

---

## Dos cosas que conviene no olvidar

**No actives el modo "serverless" ni dejes que el backend duerma.** Los
avisos de vencimiento, los de inactividad y la tasa del BCV los calcula
un bucle que vive dentro del proceso del backend. Dormido, no manda nada.

**Cuando crezca, lo primero que se queda corto es el Postgres de
Railway.** Se puede mover a Neon (gratis, con pgvector) cambiando una
sola variable — `DATABASE_URL`, recordando el `+asyncpg` y añadiendo
`?ssl=require`. El Redis, a Upstash, igual de fácil.

## Si algo falla

| Síntoma | Dónde mirar |
|---|---|
| El backend no arranca | Logs: si dice `type vector does not exist`, el Postgres no es el de pgvector |
| `/api/health` da 502 | El nombre del servicio en `BACKEND_HOST` no coincide, o falta `PORT=8000` |
| Arranca y se cae en bucle | Casi siempre `DATABASE_URL` sin `+asyncpg` |
| La web carga pero todo da error | Mira `/api/health` por separado: es el backend, no el frontend |
| Las fotos desaparecen al desplegar | Falta el volumen en `/app/media` |
| No llega ningún correo | gerencia → Sistema → "Correos (Resend)" dice el motivo exacto |
