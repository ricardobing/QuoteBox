# Variables de entorno — QuoteBox

## Railway (FastAPI backend)

Configurar en: Railway Dashboard > Proyecto QuoteBox > Variables

| Variable | Descripcion | Donde obtenerla | Ejemplo |
|----------|------------|-----------------|---------|
| `SUPABASE_URL` | URL del proyecto Supabase | Supabase Dashboard > Settings > API > Project URL | `https://buriiwhtcgxlrksbhkqo.supabase.co` |
| `SUPABASE_ANON_KEY` | Clave publica de Supabase | Supabase Dashboard > Settings > API > anon/public | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave backend con privilegios totales | Supabase Dashboard > Settings > API > service_role | `eyJhbGciOi...` |
| `SCRAPE_BASE_URL` | URL del sitio a scrapear | https://quotes.toscrape.com | `https://quotes.toscrape.com` |
| `SCRAPE_USERNAME` | Usuario de login | Dato del cliente | `ArchytasUser` |
| `SCRAPE_PASSWORD` | Contrasena de login | Dato del cliente | `123` |
| `TWILIO_ACCOUNT_SID` | SID de cuenta Twilio | Twilio Console > Account Info | `AC28989fa0...` |
| `TWILIO_AUTH_TOKEN` | Token de autenticacion Twilio | Twilio Console > Account Info | `17ed2f7a...` |
| `TWILIO_WHATSAPP_FROM` | Numero del sandbox WhatsApp | Twilio Console > Messaging > Sandbox | `whatsapp:+14155238886` |
| `RESEND_API_KEY` | API key de Resend | https://resend.com/api-keys | `re_iZoFsFrt...` |
| `NOTIFICATION_EMAIL_TO` | Email que recibe novedades | Tu email verificado en Resend | `tu@email.com` |
| `NOTIFICATION_EMAIL_FROM` | Remitente autorizado en Resend | Resend Dashboard > Domains | `QuoteBox <onboarding@resend.dev>` |
| `ESCALATION_EMAIL_TO` | Email que recibe alertas de escalacion | Tu email verificado en Resend | `tu@email.com` |
| `WEBHOOK_SECRET` | Secret para webhook de manual ingest | Generar con `python -c "import secrets; print(secrets.token_hex(32))"` | `a1b2c3...` |

### Variables opcionales

| Variable | Descripcion | Default |
|----------|------------|---------|
| `SUPABASE_DB_URL` | URL directa Postgres para scheduler | Vacio (usa MemoryJobStore) |
| `SCRAPE_INTERVAL_HOURS` | Horas entre scraping automatico | `24` |
| `UNKNOWN_AUTHOR_THRESHOLD` | Consultas para disparar escalacion | `2` |
| `FASTAPI_BASE_URL` | URL base para panel admin | `http://localhost:8000` |

---

## Streamlit Cloud (admin panel)

Configurar en: Streamlit Cloud > App Settings > Secrets

Formato TOML:

```toml
ADMIN_PASSWORD = "tu-contrasena-segura"
BACKEND_URL = "https://tu-app.railway.app"
SUPABASE_URL = "https://buriiwhtcgxlrksbhkqo.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOi..."
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOi..."
```

| Variable | Descripcion | Donde obtenerla |
|----------|------------|-----------------|
| `ADMIN_PASSWORD` | Contrasena para acceder al panel | Elegi una segura |
| `BACKEND_URL` | URL de la API FastAPI en Railway | Railway Dashboard > proyecto > Domain |
| `SUPABASE_URL` | URL del proyecto Supabase | Idem Railway |
| `SUPABASE_ANON_KEY` | Clave publica de Supabase | Idem Railway |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave backend | Idem Railway |

---

## Instrucciones de deploy

### 1. Railway (FastAPI backend)

1. Ir a https://railway.app > New Project > Deploy from GitHub
2. Seleccionar repositorio: `ricardobing/QuoteBox`
3. Branch: `master`
4. Root directory: `/` (raiz del repo)
5. Railway detecta el `Dockerfile` automaticamente
6. Ir a Variables y cargar todas las de la tabla Railway de arriba
7. Railway redeploya automaticamente al guardar variables
8. Verificar: `GET https://tu-url.railway.app/health` debe devolver `{"status":"ok"}`
9. Configurar Twilio Sandbox con la URL de Railway:
   - Twilio Console > Messaging > WhatsApp Sandbox
   - "When a message comes in": `POST https://tu-url.railway.app/webhook/whatsapp`
10. Configurar Supabase DB Webhook (ver seccion abajo)

### 2. Streamlit Cloud (admin panel)

1. Ir a https://share.streamlit.io > New app
2. Repositorio: `ricardobing/QuoteBox`
3. Branch: `master`
4. Main file path: `admin/app.py`
5. En Advanced settings > Secrets, pegar el bloque TOML de arriba
6. Click Deploy
7. Abrir la URL generada y entrar con `ADMIN_PASSWORD`

### 3. Supabase DB Webhook (manual ingest)

1. Ir a Supabase Dashboard > proyecto `buriiwhtcgxlrksbhkqo`
2. Database > Webhooks > Create a new webhook
3. Nombre: `manual_queue_insert`
4. Tabla: `public.manual_queue`
5. Eventos: `INSERT`
6. URL: `https://tu-url.railway.app/webhook/manual-ingest`
7. Method: `POST`
8. Headers: agregar `X-Webhook-Secret` con el mismo valor de `WEBHOOK_SECRET`
9. Guardar

### 4. Post-deploy verification

```bash
# 1. Health check
curl https://tu-url.railway.app/health
# → {"status":"ok","timestamp":"...","version":"0.1.0"}

# 2. Trigger scraping
curl -X POST https://tu-url.railway.app/trigger/scrape
# → {"status":"success","pages_scraped":10,"quotes_found":100,...}

# 3. WhatsApp (desde el sandbox)
# Enviar: "cuantas frases hay de Einstein"
# Respuesta esperada: "Hay 2 frases de einstein."

# 4. Manual ingest (insertar fila en Supabase manual_queue)
# La fila debe pasar a status 'approved' y aparecer en quotes
```
