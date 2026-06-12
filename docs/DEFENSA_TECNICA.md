# Defensa técnica — QuoteBox

## ¿Qué hace el sistema?

QuoteBox automatiza el proceso completo de una startup que vende frases de autores famosos por suscripción. Hoy es todo manual — alguien responde WhatsApp y mantiene planillas. El sistema reemplaza eso con:

1. **Scraping** automático de quotes.toscrape.com con login, extrayendo solo frases que coinciden con tags de interés del cliente
2. **Detección de novedades** — compara lo nuevo contra lo guardado, envía UN solo mail de resumen agrupado por tag
3. **Bot de WhatsApp** que responde consultas como "¿cuántas frases hay de Einstein?" con datos reales
4. **Escalación** automática cuando un autor desconocido se consulta repetidamente
5. **Panel admin** para que el equipo gestione tags, frases y carga manual sin tocar código

---

## ¿Por qué NO n8n?

**Esta es la pregunta más importante.** Archytas usa n8n internamente, pero para este proyecto tomé la decisión deliberada de NO usarlo.

### El problema con n8n para este caso

n8n es excelente para flujos mantenidos por perfiles no técnicos. Pero este proyecto tiene requisitos técnicos específicos que n8n resuelve mal:

| Requisito | n8n | Python/FastAPI |
|-----------|-----|----------------|
| Login con CSRF token | Requiere nodos HTTP manuales, frágil ante cambios de HTML | `BeautifulSoup` extrae el token, `requests.Session` mantiene cookies |
| Paginación dinámica | Loop con condición, difícil de debugear | `while` loop con selector CSS, 10 líneas |
| Idempotencia | Se implementa con lógica condicional en nodos | `text_hash` UNIQUE + `ON CONFLICT DO NOTHING`, una línea de SQL |
| Tests | No hay unit tests para flows | `pytest`, 30 tests en <2s |
| Versionado | JSON de flows, difícil code review | Git sobre código Python, PR revisable |
| Manejo de errores | Los nodos fallan y hay que configurar catch paths | `try/except` explícito con logs estructurados |

### Lo que reemplaza a n8n

| Componente n8n | Reemplazo | Ventaja |
|---------------|-----------|---------|
| Schedule Trigger | APScheduler dentro de FastAPI | Control explícito, `coalesce=True`, `max_instances=1` |
| Webhook nodes | Endpoints FastAPI | Validación de payload, tipos Pydantic, test automático |
| HTTP Request nodes | `requests` + `BeautifulSoup` | Sesión autenticada, timeouts, CSRF handling |
| IF/Switch nodes | `if/elif` en Python | Lógica auditable, cubierta por tests |
| Email node | Resend SDK con tenacity | 3 retries con exponential backoff |

### Cuándo SÍ usaría n8n

Si el equipo de QuoteBox crece y necesita modificar flujos sin developers, migraría triggers de negocio específicos a n8n manteniendo el core (scraper, idempotencia, WhatsApp parser) en Python.

---

## ¿Por qué Supabase?

### Alternativas evaluadas

| Opción | Ventaja | Desventaja | Decisión |
|--------|---------|------------|----------|
| **Supabase** (PostgreSQL) | SQL completo, índices, cliente Python, RLS, free tier generoso | Vendor lock-in relativo | ✅ Elegido |
| SQLite | Simple, sin infraestructura | Sin acceso remoto para webhooks, no escala horizontal | ❌ Descartado |
| MongoDB | Schema flexible | Sin constraints UNIQUE complejos, idempotencia más frágil | ❌ Descartado |
| Airtable | UI bonita para no-técnicos | Sin índices reales, rate limits, no adecuado para volúmenes | ❌ Descartado |

### Por qué PostgreSQL específicamente

- **Idempotencia**: `text_hash CHAR(64)` con índice UNIQUE. `ON CONFLICT DO NOTHING` garantiza cero duplicados a nivel base de datos, no a nivel aplicación.
- **Búsquedas flexibles**: `author_slug` con índice btree + `ILIKE` permite búsquedas parciales ("einstein" matchea "albert einstein").
- **Tags como arrays**: `tags TEXT[]` con índice GIN permite filtrar por tag de forma eficiente.
- **Webhooks nativos**: Supabase Database Webhooks disparan `net.http_post()` en cada INSERT de `manual_queue`, integrando carga manual sin polling.
- **Costo cero**: El free tier de Supabase cubre 500MB de datos y 2 proyectos. Para esta demo sobra.

---

## ¿Por qué Railway?

### Alternativas evaluadas

| Opción | Ventaja | Desventaja |
|--------|---------|------------|
| **Railway** | Deploy desde GitHub, Dockerfile nativo, variables de entorno integradas, dominio automático, free tier | Pocos proyectos en free tier |
| Fly.io | Buen free tier, regiones múltiples | Configuración más compleja (fly.toml) |
| Render | Simple, free tier para web services | Cold start en free tier (duerme el servicio) |
| Vercel | Excelente para frontend | No soporta Python/ASGI de forma nativa |

### Por qué Railway

- **Dockerfile nativo**: Mismo contenedor que en desarrollo local. Sin adaptaciones.
- **Variables de entorno integradas**: Se cargan desde el dashboard, disponibles como env vars del proceso.
- **Dominio automático**: `quotebox-production-43dc.up.railway.app` sin configurar DNS.
- **GitHub integration**: Push a `master` → deploy automático (cuando se configura).
- **APScheduler funciona**: `--workers 1` en el CMD es suficiente para el scheduler embebido.

---

## ¿Por qué Twilio para WhatsApp?

| Opción | Ventaja | Desventaja |
|--------|---------|------------|
| **Twilio Sandbox** | Free trial sin tarjeta, SDK Python, webhook simple | Usuarios deben unirse al sandbox |
| Meta Cloud API | Canal oficial de WhatsApp | Requiere verificación de negocio, más burocrático |
| WhatsApp Business | App móvil, simple | No tiene API programática |

### Por qué Twilio para la demo
- Onboarding en 5 minutos: crear cuenta → obtener SID/token → configurar webhook.
- Webhook HTTP POST directo al endpoint de Railway.
- SDK Python maduro: `twilio.twiml.messaging_response.MessagingResponse` para respuestas.
- En producción migraría a Meta Cloud API: 1000 conversaciones/mes gratis, sin requisito de unirse al sandbox.

---

## ¿Por qué FastAPI?

- **Alto rendimiento**: ASGI con uvicorn, comparable a Node.js/Go para tráfico HTTP.
- **Tipado fuerte**: Pydantic valida todos los inputs y outputs automáticamente.
- **Documentación automática**: `/docs` con Swagger UI, interactiva, sin escribir un solo comentario.
- **Un solo proceso**: Scraper + scheduler + webhooks + API en un mismo servicio. Sin microservicios innecesarios.

---

## ¿Por qué APScheduler dentro de FastAPI?

- **Sin infraestructura extra**: No requiere Redis, Celery ni worker separado.
- **Control explícito**: `max_instances=1` + `coalesce=True` evitan ejecuciones solapadas.
- **Persistencia opcional**: `SQLAlchemyJobStore` si hay `SUPABASE_DB_URL`, `MemoryJobStore` en dev.
- **Evolución**: Si se necesita escalar horizontalmente, se separa el scheduler a un Railway Cron Job independiente.

---

## ¿Cómo se integran los componentes?

```
Usuario WhatsApp
    │
    ▼
Twilio Sandbox ──POST──▶ Railway (FastAPI) ◀──HTTP── Streamlit Cloud (admin)
                              │    ▲
                              │    │
                              ▼    │
                          Supabase PostgreSQL
                              │    ▲
                              │    │
                         pg_net trigger (INSERT manual_queue → webhook)
```

**Flujo de scraping:**
1. APScheduler dispara job cada 24h (o trigger manual desde admin)
2. `session.py` hace login con CSRF
3. `crawler.py` recorre todas las páginas, extrae quotes
4. `ingestor.py` filtra por tags activos, normaliza texto, calcula hash, upsert con ON CONFLICT DO NOTHING
5. Si hay nuevas: `email.py` agrupa por tag y envía UN mail con tenacity (3 retries)
6. `scrape_runs` registra métricas de cada corrida

**Flujo de WhatsApp:**
1. Twilio webhook → `POST /webhook/whatsapp`
2. `whatsapp.py` parsea el mensaje (COUNT/LIST/UNKNOWN)
3. `quotes.py` consulta Supabase por `author_slug ILIKE`
4. Si no encuentra: `escalation.py` registra en `unknown_author_requests` + evalúa threshold
5. Respuesta en TwiML XML

**Flujo de carga manual (dos vías):**
1. **Streamlit**: POST a `/admin/quotes/manual` → validación → upsert en `quotes`
2. **Supabase webhook**: INSERT en `manual_queue` → trigger `pg_net` → POST a `/webhook/manual-ingest` → upsert + actualiza estado

---

## Criterios de evaluación cubiertos

| Criterio | Cómo se cumple |
|----------|---------------|
| Trigger correcto | APScheduler + endpoint manual `/trigger/scrape` |
| Retry en llamadas externas | tenacity: 3 intentos, exponential backoff (1s, 2s, 4s) en emails |
| Secretos no hardcodeados | `.env` + `.env.example` + Railway variables. Cero secretos en código. |
| Idempotencia | `text_hash` UNIQUE a nivel DB. QA confirma 0 duplicados tras 3 corridas. |
| Manejo de errores | Cada capa tiene try/except explícito. Errores persisten en `scrape_runs` y `manual_queue`. Errores de email no bloquean el scraper. |
| Diseño del flujo completo | Dos fuentes de datos (scraping + manual), un bot, escalación, panel admin. |
| Tags configurables sin código | Streamlit CRUD. Agregar tag → siguiente scrape lo detecta automáticamente. |
| Claridad | README con arquitectura, setup, endpoints. `decisions.md` con justificaciones. |
| Escalabilidad | Más tags = tabla parametrizable. Más consultas = índice en `author_slug`. Más volumen = separar scheduler del backend. |

---

## ¿Qué haría diferente en producción?

1. **Meta WhatsApp Cloud API** en vez de Twilio Sandbox: canal oficial, sin requisito de unirse al sandbox, 1000 conversaciones/mes gratis.
2. **Activar RLS en Supabase** con políticas por rol (hoy está desactivado para simplificar el demo).
3. **Railway Cron Job** separado para el scheduler, permitiendo escalar el backend horizontalmente.
4. **Sentry** para monitoreo de errores con alertas en tiempo real.
5. **Secretos rotables** con vault (Infisical, Doppler) en lugar de variables de entorno estáticas.
6. **CI/CD pipeline** con GitHub Actions: tests automáticos antes de mergear a main.
7. **Rate limiting** en los endpoints públicos para prevenir abuso del webhook de WhatsApp.
