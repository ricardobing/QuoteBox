# Decisiones de arquitectura — QuoteBox

## 1) Decisión no negociable: NO n8n

Esta implementación **no usa n8n** por decisión previa validada con el cliente (Archytas).

### Justificación

n8n agrega valor cuando los flujos son mantenidos por perfiles no técnicos. En este caso, toda la lógica la mantiene un developer.

El problema central (scraping con login CSRF, sesión autenticada, paginación, idempotencia, retries, manejo de errores) es más robusto en Python puro que en un flujo visual con nodos HTTP.

Se reemplazan piezas típicas de n8n por componentes de código:

- `Schedule Trigger` → `APScheduler` + `SQLAlchemyJobStore`
- `Webhook nodes` → endpoints `FastAPI`
- lógica condicional y deduplicación → servicios Python testeables

### Beneficios concretos

- Menos piezas móviles
- Logs estructurados
- Manejo explícito de excepciones
- Unit tests reales por módulo
- Versionado y code review sobre código, no sobre JSON de flows

---

## 2) Backend: FastAPI (monolito modular)

Se usa un único servicio FastAPI para:

- Scraper autenticado (`requests` + `BeautifulSoup`)
- Scheduler interno (corrida cada 24h + trigger manual)
- Webhooks (Twilio + ingest manual)
- API de health

Razón: para este scope evita complejidad innecesaria de microservicios y mantiene bajo costo operativo.

---

## 3) Scheduler: APScheduler dentro de FastAPI

### Decisión

Sí, se usa APScheduler embebido, con `SQLAlchemyJobStore` cuando hay `SUPABASE_DB_URL`, y fallback a `MemoryJobStore` en dev.

### Restricción operativa

El proceso web corre con `--workers 1`. Con múltiples workers se duplicaría la ejecución de jobs.

### Evolución futura

Si crece el volumen o se requiere escalado horizontal, separar scheduler a worker dedicado o migrar a cola (ej. Celery + Redis).

---

## 4) Scraping strategy

No se scrapea por tag (evita multiplicar requests). Se hace:

1. Login con CSRF token
2. Recorrido completo de paginación (`Next`) una sola vez
3. Filtro en memoria por `monitored_tags` activos

Esto reduce latencia, tráfico y riesgo de inconsistencias.

---

## 5) Storage: Supabase Postgres

Tablas principales:

- `quotes`
- `monitored_tags`
- `unknown_author_requests`
- `manual_queue`
- `scrape_runs`

### Idempotencia

Se usa `text_hash` (SHA-256 de texto normalizado) con UNIQUE.
Inserción con conflicto ignorado evita duplicados al re-ejecutar scraping.

### Estados de frase

- `active = false`: desactivada por humano, no se reactiva automáticamente
- eliminación física: si la frase reaparece en scraping, entra como novedad

---

## 6) Panel admin: Streamlit

Servicio separado para operaciones simples:

- CRUD de `monitored_tags`
- disparo manual de scraping
- activación/desactivación de frases

Razón: entrega rápida, baja complejidad y mantenimiento simple para tooling interno.

---

## 7) WhatsApp: Twilio Sandbox

Se eligió Twilio Sandbox por:

- onboarding rápido en free trial
- webhook HTTP directo y estable
- SDK Python maduro

Intents mínimos:

- COUNT por autor
- LIST por autor
- autor desconocido (registro + posible escalación)

---

## 8) Escalación de autores desconocidos

Cada consulta sin match se persiste en `unknown_author_requests`.

Cuando `author_normalized` alcanza umbral (2+ consultas) y no fue escalado, se envía email por Resend y se marca `escalated = true` para no repetir alertas.

---

## 9) Email: Resend

Se usa Resend por SDK limpio y free tier adecuado.

Se envían:

- resumen único de novedades (agrupado por tag) por corrida con hallazgos
- alerta de escalación por autor desconocido recurrente

---

## 10) Secret management

No hay secretos hardcodeados. Todo en variables de entorno (`.env`).

- `.env.example` documenta contrato de configuración
- `.env` está ignorado por git
- claves de Supabase/Twilio/Resend solo en entorno de ejecución

---

## 11) Manejo de errores

Cada capa maneja errores de forma explícita:

- scraper: excepciones de red, parseo, login
- DB: errores de inserción y conflictos
- webhooks: validación de payload
- scheduler: captura y persistencia en `scrape_runs`

No se silencian fallos.

---

## 12) Escalabilidad

El diseño soporta crecimiento sin reescritura:

- más tags: tabla parametrizable
- más consultas WhatsApp: query indexada por `author_slug`
- más volumen de scraping: posible separación del scheduler/worker
- más canales: capa de servicios desacoplada
