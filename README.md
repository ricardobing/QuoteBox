# QuoteBox

Automatización end-to-end para scraping de frases, detección de novedades, panel admin y bot de WhatsApp.

> Decisión de arquitectura confirmada con cliente: **no se usa n8n**.

## 1) Requisitos previos

1. **Python 3.12+**
2. **Docker Desktop** (opcional, para correr por contenedores)
3. **Cuenta Supabase** (proyecto ya creado)
4. **Twilio Sandbox para WhatsApp**
5. **Resend API key**

## 2) Clonar y preparar entorno

1. Entrar al proyecto:
   - `cd c:\tmp\quotebox`
2. Crear entorno virtual:
   - `python -m venv .venv`
3. Activar entorno en PowerShell:
   - `.\.venv\Scripts\Activate.ps1`
4. Instalar dependencias:
   - `pip install -r requirements.txt`

## 3) Variables de entorno

1. Copiar template:
   - `copy .env.example .env`
2. Completar cada variable en `.env`:
   - Supabase URL + keys
   - Credenciales de scraping
   - Twilio credentials
   - Resend API key y emails
   - `WEBHOOK_SECRET`

## 4) Estructura del proyecto

- `app/` → API FastAPI, scheduler, scraper, servicios
- `admin/` → panel Streamlit
- `tests/` → suite de tests unitarios
- `docs/decisions.md` → justificación de decisiones técnicas
- `schema.sql` → schema completo de Supabase

## 5) Correr API local

Con entorno virtual activo:

- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 1`

Health check:

- `GET http://localhost:8000/health`

## 6) Correr panel admin local

En otra terminal:

1. `cd admin`
2. `pip install -r requirements.txt`
3. `streamlit run app.py --server.port 8501`

Panel:

- http://localhost:8501

## 7) Correr con Docker Compose

Desde raíz:

- `docker-compose up --build`

Servicios:

- API: http://localhost:8000
- Admin: http://localhost:8501

## 8) Endpoints principales

- `GET /health`
- `POST /trigger/scrape`
- `POST /webhook/whatsapp` (Twilio)
- `POST /webhook/manual-ingest` (Supabase DB webhook)

## 9) Idempotencia

La tabla `quotes` usa `text_hash` (SHA-256 del texto normalizado) con índice UNIQUE.
Inserciones nuevas se hacen con `ON CONFLICT (text_hash) DO NOTHING`.
Resultado: ejecutar scraping repetido **no duplica** frases.

## 10) Deploy

### FastAPI en Railway

1. Conectar repo a Railway.
2. Seleccionar servicio con `Dockerfile` raíz.
3. Cargar variables `.env` en Railway.
4. Verificar `GET /health`.

### Streamlit Cloud

1. Crear app apuntando a `admin/app.py`.
2. Cargar secretos (mismas variables relevantes: Supabase + FASTAPI_BASE_URL).
3. Deploy.

## 11) Testing

Desde raíz:

- `pytest -q`

## 12) Notas de operación

- `--workers 1` es obligatorio mientras APScheduler corre dentro de FastAPI.
- Para escalar horizontalmente, mover scheduler a worker separado.
