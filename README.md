# QuoteBox — Sistema automatizado de frases

Scraping autenticado de quotes.toscrape.com con detección de novedades, bot de WhatsApp, panel admin y carga manual.

## Arquitectura

```
                   ┌─────────────┐
                   │  Streamlit  │  admin (CRUD tags, carga manual, trigger)
                   └──────┬──────┘
                          │ HTTP
                          ▼
┌──────────┐  webhook  ┌───────────┐  SQL  ┌──────────┐
│  Twilio  │──────────▶│  FastAPI   │──────▶│ Supabase │
│WhatsApp  │◀──────────│ (monolito) │◀──────│PostgreSQL│
└──────────┘  TwiML    └─────┬─────┘       └──────────┘
                             │
                    ┌────────┴────────┐
                    │   APScheduler   │  job diario
                    │  MemoryJobStore │  scrape + mail
                    └─────────────────┘
```

Componentes: **FastAPI** (scraper, webhooks, scheduler, API) → **Supabase** (storage), **Twilio** (WhatsApp), **Resend** (email), **Streamlit** (panel admin).

## Stack y decisiones

| Tecnología | Rol | Por qué |
|-----------|-----|---------|
| **FastAPI** | Backend unificado | Un solo servicio para scraper, scheduler, webhooks y API. Evita complejidad de microservicios sin sacrificar testabilidad. |
| **Supabase** | PostgreSQL gestionado | Storage relacional con índices, idempotencia vía `text_hash` UNIQUE, cliente Python nativo. Sin infraestructura que mantener. |
| **Twilio** | WhatsApp sandbox | Webhook HTTP directo, SDK Python maduro, free trial sin tarjeta. Alternativa: Meta Cloud API en producción. |
| **Resend** | Email transaccional | SDK mínima, free tier para 100 emails/día, retry con tenacity. |
| **Streamlit** | Panel admin | CRUD de tags y frases en ~100 líneas. Ideal para tooling interno sin frontend. |
| **APScheduler** | Job scheduling | Corre dentro del proceso FastAPI (`--workers 1`), reemplaza triggers visuales de n8n. |

**No n8n:** toda la lógica vive en código Python versionado y testeable. Un developer mantiene esto sin depender de flows JSON ni interfaces drag-and-drop.

## Funcionalidades

- [x] Scraping autenticado con CSRF + paginación completa
- [x] Filtro por tags activos (love, humor, life, inspirational + los que se agreguen)
- [x] Idempotencia: re-ejecutar no duplica frases (`text_hash` UNIQUE)
- [x] Detección de novedades: un solo mail agrupado por tag (Resend)
- [x] Tags configurables sin tocar código (Streamlit admin)
- [x] WhatsApp bot: COUNT por autor, LIST por autor, follow-up contextual
- [x] Autores desconocidos: registro + escalación automática al 2do request
- [x] Carga manual con formulario Streamlit → validación → upsert idempotente
- [x] Frases desactivadas persisten inactivas tras scrape
- [x] Frases eliminadas reaparecen como novedad si el scraper las reencuentra
- [x] Nuevo tag → corrida siguiente detecta frases con ese tag
- [x] Panel admin con auth, métricas, y trigger manual de scraping
- [x] Tests unitarios para scraper, WhatsApp parser e ingestor (30 tests)

## Setup local

```bash
# 1. Clonar y crear venv
git clone https://github.com/ricardobing/QuoteBox.git
cd QuoteBox
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows
# source .venv/bin/activate    # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear .env desde el template y completar valores
cp .env.example .env

# 4. Aplicar schema en Supabase (via MCP o copiando schema.sql en SQL Editor)
# schema.sql crea 5 tablas + 4 seeds de tags

# 5. Levantar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verificar
curl http://localhost:8000/health
# → {"status":"ok","timestamp":"...","version":"0.1.0"}
```

## Variables de entorno

| Variable | Descripción | Dónde obtener |
|----------|------------|---------------|
| `SUPABASE_URL` | URL del proyecto | Supabase Dashboard > Settings > API |
| `SUPABASE_ANON_KEY` | Clave pública | Supabase Dashboard > Settings > API |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave backend | Supabase Dashboard > Settings > API |
| `SCRAPE_BASE_URL` | Sitio a scrapear | `https://quotes.toscrape.com` |
| `SCRAPE_USERNAME` | Login del scraper | Credenciales del cliente |
| `SCRAPE_PASSWORD` | Contraseña del scraper | Credenciales del cliente |
| `TWILIO_ACCOUNT_SID` | SID de Twilio | Twilio Console > Account Info |
| `TWILIO_AUTH_TOKEN` | Token de Twilio | Twilio Console > Account Info |
| `TWILIO_WHATSAPP_FROM` | Número sandbox | Twilio Console > Messaging > Sandbox |
| `RESEND_API_KEY` | API key Resend | https://resend.com/api-keys |
| `NOTIFICATION_EMAIL_TO` | Destino novedades | Email verificado en Resend |
| `NOTIFICATION_EMAIL_FROM` | Remitente | `onboarding@resend.dev` en dev |
| `ESCALATION_EMAIL_TO` | Destino escalaciones | Email verificado en Resend |
| `WEBHOOK_SECRET` | Secret manual ingest | Generar con `secrets.token_hex(32)` |
| `SCRAPE_INTERVAL_HOURS` | Horas entre jobs | Default: `24` |
| `UNKNOWN_AUTHOR_THRESHOLD` | Requests para escalar | Default: `2` |

## Endpoints

| Método | Path | Descripción | Respuesta |
|--------|------|-------------|-----------|
| `GET` | `/health` | Health check | `{"status":"ok","timestamp":"...","version":"0.1.0"}` |
| `POST` | `/trigger/scrape` | Disparo manual de scraping | `{"status":"success","pages_scraped":10,"quotes_found":100,"quotes_new":0}` |
| `POST` | `/webhook/whatsapp` | Webhook Twilio entrante | TwiML XML con respuesta |
| `POST` | `/webhook/manual-ingest` | Webhook Supabase DB | `{"ok":true,"detail":"..."}` |
| `POST` | `/admin/quotes/manual` | Carga manual (admin) | `201` creado, `409` duplicado |

## Tests

```bash
pytest tests/ -v     # 30 tests en < 2s
```

Cobertura: normalización de texto (hash determinista), scraper (login CSRF, parseo HTML, paginación), WhatsApp (parseo de intents, limpieza de autor, follow-up contextual), ingestor (upsert idempotente, filtrado por tags, mock Supabase).

## Deploy

| Componente | Plataforma | URL |
|-----------|-----------|-----|
| **Backend** | Railway | `https://quotebox-production-43dc.up.railway.app` |
| **Admin** | Streamlit Cloud | Configurar `admin/app.py` con secrets |

Para deployar Streamlit Cloud: ir a https://share.streamlit.io, repo `ricardobing/QuoteBox`, branch `master`, main file `admin/app.py`, y cargar en Secrets el bloque TOML de `docs/ENV_VARIABLES.md`.

## Estructura del proyecto

```
QuoteBox/
├── app/                    # Backend FastAPI
│   ├── main.py             # App factory, lifecycle hooks
│   ├── config.py           # Settings desde env vars (pydantic)
│   ├── database.py         # Clientes Supabase + SQLAlchemy
│   ├── scheduler.py        # APScheduler factory + jobs
│   ├── scraper/            # Módulo de scraping
│   │   ├── session.py      # Sesión HTTP + login CSRF
│   │   ├── crawler.py      # Paginación + parseo HTML
│   │   └── ingestor.py     # Normalización + upsert idempotente
│   ├── services/           # Lógica de dominio
│   │   ├── quotes.py       # Consultas y upsert de frases
│   │   ├── tags.py         # CRUD de tags monitoreados
│   │   ├── whatsapp.py     # Parseo de intents + respuestas
│   │   ├── email.py        # Envíos Resend con tenacity
│   │   └── escalation.py   # Registro y escalación de autores
│   ├── routers/            # Endpoints HTTP
│   │   ├── health.py       # GET /health
│   │   ├── trigger.py      # POST /trigger/scrape
│   │   ├── webhooks.py     # Twilio + manual ingest
│   │   └── admin.py        # POST /admin/quotes/manual
│   └── models/             # Schemas Pydantic
├── admin/                  # Panel Streamlit
│   ├── app.py              # Home: auth, métricas, trigger
│   └── pages/              # Páginas del panel
│       ├── 1_Tags.py       # CRUD de tags monitoreados
│       ├── 2_Quotes.py     # Vista y filtro de frases
│       └── 3_Carga_Manual.py  # Formulario de carga manual
├── tests/                  # Suite de tests
│   ├── test_scraper.py     # Login, parseo, crawl, idempotencia
│   ├── test_whatsapp.py    # Intents, limpieza, follow-up
│   └── test_ingestor.py    # Normalización, upsert mock
├── docs/
│   ├── decisions.md        # Decisiones de arquitectura
│   └── ENV_VARIABLES.md    # Variables reales + pasos deploy (local)
├── schema.sql              # Schema completo de Supabase
├── Dockerfile              # Imagen para Railway
├── requirements.txt        # Dependencias Python
└── .env.example            # Template de variables de entorno
```
