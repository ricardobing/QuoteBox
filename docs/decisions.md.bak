# Decisiones de arquitectura — QuoteBox

## 1) NO n8n — lógica en código

Esta implementación **no usa n8n** por decisión validada con el cliente (Archytas). n8n agrega valor cuando los flujos los mantienen perfiles no técnicos; aquí toda la lógica la mantiene un developer. El scraping con login CSRF, paginación, idempotencia y manejo de errores es más robusto en Python puro que en un flujo visual.

Se reemplazan nodos típicos de n8n por: APScheduler (Schedule Trigger), endpoints FastAPI (Webhook nodes), servicios Python testeables (lógica condicional y deduplicación). Beneficios: menos piezas móviles, logs estructurados, unit tests reales y versionado sobre código.

## 2) Backend: FastAPI + APScheduler

Un único servicio FastAPI agrupa scraper, scheduler, webhooks (Twilio + ingest manual) y API de health. APScheduler corre embebido con `SQLAlchemyJobStore` (o `MemoryJobStore` en dev). Restricción operativa: `--workers 1` obligatorio para evitar duplicación de jobs.

## 3) Scraping: una sola pasada

No se scrapea por tag (evita multiplicar requests). Flujo: login con CSRF token → paginación completa siguiendo `Next` → filtro en memoria por `monitored_tags` activos. Reduce latencia, tráfico y riesgo de inconsistencias.

## 4) Storage: Supabase Postgres

Tablas: `quotes`, `monitored_tags`, `unknown_author_requests`, `manual_queue`, `scrape_runs`. Idempotencia vía `text_hash` (SHA-256 del texto normalizado) con índice UNIQUE: inserciones con `ON CONFLICT DO NOTHING` evitan duplicados. Estados de frase: `active = false` (desactivada por humano, el scraper no la reactiva); eliminación física (si reaparece en scraping, entra como novedad).

## 5) Panel admin: Streamlit

Servicio separado para CRUD de `monitored_tags`, disparo manual de scraping, activación/desactivación de frases y carga manual. Streamlit permite entrega rápida con mantenimiento simple para tooling interno.

## 6) WhatsApp: Twilio Sandbox

Se eligió Twilio Sandbox por onboarding rápido en free trial, webhook HTTP directo y SDK Python maduro. Intents: COUNT por autor, LIST por autor y autor desconocido con registro + escalación.

## 7) Escalación de autores desconocidos

Cada consulta sin match se persiste en `unknown_author_requests`. Cuando un autor normalizado alcanza el umbral (2+ consultas) sin haber sido escalado, se envía email vía Resend y se marca `escalated = true` para no repetir alertas.

## 8) Email: Resend

SDK limpio y free tier adecuado. Se envían: resumen único de novedades agrupado por tag (uno por corrida con hallazgos) y alerta de escalación por autor desconocido recurrente. Reintentos con tenacity (3 attempts, exponential backoff).

## 9) Secretos y errores

Credenciales solo en variables de entorno (`.env` ignorado por git, `.env.example` documenta el contrato). Cada capa maneja errores explícitamente: scraper (red, parseo, login), DB (inserción y conflictos), webhooks (validación de payload) y scheduler (persistencia en `scrape_runs`). No se silencian fallos.

## 10) ¿Qué haría diferente en producción?

- **Meta WhatsApp Cloud API** en lugar de Twilio Sandbox: elimina la necesidad de que usuarios se unan al sandbox, ofrece 1000 conversaciones/mes gratis y es el canal oficial.
- **Activar RLS en Supabase** con políticas por rol (hoy está desactivado para simplificar el demo).
- **Railway Cron Job** separado para el scheduler: permite escalar el backend horizontalmente sin duplicar jobs.
- **Sentry** para monitoreo de errores en producción con alertas en tiempo real.
- **Secretos rotables**: usar un vault (ej. Infisical o Doppler) en lugar de variables de entorno estáticas, con rotación automática y audit log.
