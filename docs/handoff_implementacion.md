# Handoff de implementación (E1 → E11)

Este documento es la guía operativa completa para continuar el proyecto sin contexto previo.

Regla global: no implementar n8n ni sugerirlo. Toda la lógica vive en FastAPI + Python + Supabase + Streamlit.

---

**Etapa 1 — Implementación del scraper**
- Objetivo: implementar scraping autenticado end-to-end (login CSRF + paginación completa), filtrar por tags activos, persistir idempotente en `quotes` y registrar corrida en `scrape_runs`.
- Archivos a modificar/completar: 
  - app/scraper/session.py
  - app/scraper/crawler.py
  - app/scraper/ingestor.py
- Por cada archivo:
  - app/scraper/session.py
    - Qué imports necesita:
      - `logging`
      - `typing.Final`
      - `requests`
      - `bs4.BeautifulSoup`
      - `app.config.Settings`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def build_http_session() -> requests.Session`
        - Qué hace exactamente:
          1) Crea `requests.Session`.
          2) Configura headers (`User-Agent`, `Accept-Language`).
          3) Configura timeouts por request vía helper interno (no global de requests).
        - Casos de error que debe manejar:
          - No hay error esperado al construir sesión; si falla, propagar excepción.
        - Si usa tenacity: no aplica.
      - Firma completa: `def login_with_csrf(session: requests.Session, settings: Settings) -> None`
        - Qué hace exactamente:
          1) GET a `{SCRAPE_BASE_URL}/login`.
          2) Parsea HTML y extrae `input[name='csrf_token']`.
          3) POST a `/login` con `username`, `password`, `csrf_token`.
          4) Verifica autenticación comprobando presencia de `Logout` o ausencia de `Login` en HTML de respuesta.
          5) Deja cookies de sesión en `session` para crawling posterior.
        - Casos de error que debe manejar:
          - Error de red (`requests.RequestException`) en GET/POST.
          - CSRF no encontrado.
          - Credenciales inválidas (respuesta no autenticada).
          - HTML inesperado.
        - Si usa tenacity: no usar en esta etapa.
  - app/scraper/crawler.py
    - Qué imports necesita:
      - `dataclasses.dataclass`
      - `typing.Iterable`
      - `urllib.parse.urljoin`
      - `requests`
      - `bs4.BeautifulSoup`
      - `app.config.Settings`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def parse_quotes_from_html(html: str) -> Iterable[RawQuote]`
        - Qué hace exactamente:
          1) Parsea HTML con `lxml`.
          2) Recorre cada bloque `.quote`.
          3) Extrae texto (`.text`), autor (`.author`) y tags (`.tag`).
          4) Limpia comillas tipográficas y espacios extremos.
          5) Devuelve iterable de `RawQuote`.
        - Casos de error que debe manejar:
          - HTML inválido o estructura ausente.
          - Quote incompleta (texto o autor faltante): descartar esa quote y loggear warning.
        - Si usa tenacity: no aplica.
      - Firma completa: `def crawl_all_quotes(session: requests.Session, settings: Settings) -> CrawlResult`
        - Qué hace exactamente:
          1) Arranca en `/` o `/page/1/`.
          2) GET secuencial de todas las páginas siguiendo link `li.next > a`.
          3) En cada página usa `parse_quotes_from_html()`.
          4) Acumula todas las quotes sin filtrar por tag todavía.
          5) Corta cuando no hay `next`.
          6) Retorna `CrawlResult(pages_scraped, quotes)`.
        - Casos de error que debe manejar:
          - Error HTTP en una página.
          - Parseo fallido global.
          - Loop infinito por paginación defectuosa: proteger con set de URLs visitadas.
        - Si usa tenacity: no aplica.
  - app/scraper/ingestor.py
    - Qué imports necesita:
      - `hashlib`
      - `re`
      - `datetime.datetime`, `datetime.timezone`
      - `collections.defaultdict`
      - `supabase.Client`
      - `app.scraper.crawler.RawQuote`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def normalize_text_for_hash(text: str) -> str`
        - Qué hace exactamente: trim, lowercase, colapsar whitespace múltiple a un espacio.
        - Casos de error que debe manejar: input vacío (retorna cadena vacía normalizada).
        - Si usa tenacity: no aplica.
      - Firma completa: `def compute_text_hash(text: str) -> str`
        - Qué hace exactamente: SHA-256 hex del texto normalizado UTF-8.
        - Casos de error que debe manejar: input no string (TypeError explícito).
        - Si usa tenacity: no aplica.
      - Firma completa: `def normalize_author(author: str) -> str`
        - Qué hace exactamente: trim + lowercase + colapsar espacios.
        - Casos de error que debe manejar: input vacío.
        - Si usa tenacity: no aplica.
      - Firma completa: `def upsert_quotes_idempotent(supabase: Client, quotes: list[RawQuote], active_tags: set[str]) -> IngestResult`
        - Qué hace exactamente:
          1) Filtra quotes por intersección entre `quote.tags` y `active_tags`.
          2) Para cada quote calcula `normalized_text`, `text_hash`, `author_slug`.
          3) Arma payload con `source='scraper'`, `active=True`, timestamps.
          4) Inserta en lotes usando `on_conflict='text_hash'` y `ignore_duplicates=True`.
          5) En conflicto: no duplica.
          6) Retorna métricas (`quotes_seen`, `quotes_inserted`).
        - Casos de error que debe manejar:
          - Error de Supabase en insert.
          - Quote con texto/autor inválido.
        - Si usa tenacity: no aplica.
      - Firma completa: `def record_scrape_run(supabase: Client, status: str, pages_scraped: int, quotes_found: int, quotes_new: int, error_detail: str | None = None) -> None`
        - Qué hace exactamente: inserta fila final en `scrape_runs` con `started_at`/`finished_at` y métricas.
        - Casos de error que debe manejar: error de escritura; loggear y propagar.
        - Si usa tenacity: no aplica.
- Variables de entorno que consume esta etapa:
  - `SCRAPE_BASE_URL`
  - `SCRAPE_USERNAME`
  - `SCRAPE_PASSWORD`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta:
    1) Ejecutar `POST /trigger/scrape`.
    2) Consultar en Supabase: `quotes` (debe tener inserts), `scrape_runs` (debe tener una fila nueva).
    3) Repetir trigger y verificar que `quotes` no aumenta con duplicados.
- Dependencias: qué etapas anteriores tienen que estar completas:
  - Ninguna.

---

**Etapa 2 — Servicios de quotes y tags**
- Objetivo: completar capa de acceso a datos para frases y tags, reutilizable por routers, scraper y bot.
- Archivos a modificar/completar:
  - app/services/quotes.py
  - app/services/tags.py
- Por cada archivo:
  - app/services/quotes.py
    - Qué imports necesita:
      - `typing.Any`
      - `supabase.Client`
      - `app.scraper.ingestor.normalize_author`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def count_quotes_by_author(supabase: Client, author_query: str) -> int`
        - Qué hace exactamente:
          1) Normaliza `author_query` → `author_slug`.
          2) Query a `quotes` con `active=True` y `author_slug ilike %valor%`.
          3) Retorna count exacto.
        - Casos de error que debe manejar: errores de Supabase, query vacía.
        - Si usa tenacity: no aplica.
      - Firma completa: `def list_quotes_by_author(supabase: Client, author_query: str, limit: int = 10) -> list[dict[str, Any]]`
        - Qué hace exactamente:
          1) Normaliza autor.
          2) Consulta `quotes` activas por `author_slug ilike`.
          3) Ordena por `created_at desc`.
          4) Aplica `limit` máximo 50.
          5) Retorna lista con `id,text,author,tags,active`.
        - Casos de error que debe manejar: límites inválidos, error Supabase.
        - Si usa tenacity: no aplica.
      - Firma completa: `def upsert_quote_manual(supabase: Client, text: str, author: str, tags: list[str]) -> dict[str, Any]`
        - Qué hace exactamente:
          1) Normaliza y calcula hash.
          2) Upsert en `quotes` con `source='manual'` y conflicto por `text_hash`.
          3) Retorna fila insertada o existente.
        - Casos de error que debe manejar: campos vacíos, error DB.
        - Si usa tenacity: no aplica.
      - Firma completa: `def set_quote_active_status(supabase: Client, quote_id: str, active: bool) -> None`
        - Qué hace exactamente: update `quotes.active` por `id`.
        - Casos de error que debe manejar: id inexistente, error update.
        - Si usa tenacity: no aplica.
  - app/services/tags.py
    - Qué imports necesita:
      - `typing.Any`
      - `supabase.Client`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def list_monitored_tags(supabase: Client, only_active: bool = False) -> list[dict[str, Any]]`
        - Qué hace exactamente: select de `monitored_tags`, opcional `active=True`, orden alfabético.
        - Casos de error: error query.
        - Si usa tenacity: no aplica.
      - Firma completa: `def get_active_tags(supabase: Client) -> set[str]`
        - Qué hace exactamente: devuelve conjunto lowercase de tags activos.
        - Casos de error: error query.
        - Si usa tenacity: no aplica.
      - Firma completa: `def create_monitored_tag(supabase: Client, tag: str, active: bool = True) -> dict[str, Any]`
        - Qué hace exactamente: insert de tag normalizado.
        - Casos de error: duplicado por índice único `lower(tag)`, error insert.
        - Si usa tenacity: no aplica.
      - Firma completa: `def update_monitored_tag(supabase: Client, tag_id: str, *, tag: str | None = None, active: bool | None = None) -> None`
        - Qué hace exactamente: update parcial por id.
        - Casos de error: id inexistente, payload vacío.
        - Si usa tenacity: no aplica.
      - Firma completa: `def delete_monitored_tag(supabase: Client, tag_id: str) -> None`
        - Qué hace exactamente: delete por id.
        - Casos de error: id inexistente, error delete.
        - Si usa tenacity: no aplica.
- Variables de entorno que consume esta etapa:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta: usar REPL o endpoint de prueba para invocar cada función y confirmar cambios en tablas `quotes` y `monitored_tags`.
- Dependencias: E1 completa.

---

**Etapa 3 — Router trigger y health**
- Objetivo: exponer endpoints operativos mínimos para disparar scraping manual y validar estado de servicio.
- Archivos a modificar/completar:
  - app/routers/trigger.py
  - app/routers/health.py
  - app/models/schemas.py
- Por cada archivo:
  - app/models/schemas.py
    - Qué imports necesita:
      - `datetime.datetime`
      - `typing.Literal`
      - `pydantic.BaseModel`, `pydantic.Field`
    - Cada función/método que hay que implementar con:
      - Firma completa: `class ScrapeResult(BaseModel)`
        - Campos: `status: Literal['success','error','partial']`, `pages_scraped: int`, `quotes_found: int`, `quotes_new: int`, `run_id: str | None`, `error_detail: str | None`.
      - Firma completa: `class HealthResponse(BaseModel)`
        - Campos: `status: Literal['ok']`, `timestamp: datetime`, `version: str`.
  - app/routers/trigger.py
    - Qué imports necesita:
      - `logging`
      - `fastapi.APIRouter`, `fastapi.Request`, `fastapi.HTTPException`
      - `app.models.schemas.ScrapeResult`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def trigger_scrape(request: Request) -> ScrapeResult`
        - Qué hace exactamente:
          1) Obtiene `supabase` y `settings` desde `request.app.state`.
          2) Ejecuta pipeline E1 síncrono (login, crawl, ingest, record run).
          3) Devuelve `ScrapeResult` con métricas reales.
        - Casos de error:
          - cualquier excepción del pipeline → HTTP 500 con `ScrapeResult(status='error', ...)`.
        - Si usa tenacity: no aplica.
  - app/routers/health.py
    - Qué imports necesita:
      - `datetime.datetime`, `datetime.timezone`
      - `fastapi.APIRouter`
      - `app.models.schemas.HealthResponse`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def health() -> HealthResponse`
        - Qué hace exactamente: responde `status='ok'`, `timestamp` UTC, `version` fija desde `app.main`.
        - Casos de error: ninguno esperado.
        - Si usa tenacity: no aplica.
- Variables de entorno que consume esta etapa:
  - ninguna adicional (usa estado ya configurado).
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - `curl http://localhost:8000/health`
  - `curl -X POST http://localhost:8000/trigger/scrape`
- Dependencias: E1 y E2 completas.

---

**Etapa 4 — Email con Resend**
- Objetivo: enviar correos operativos (novedades, escalación, error de ingest manual) con reintentos robustos.
- Archivos a modificar/completar:
  - app/services/email.py
- Por cada archivo:
  - app/services/email.py
    - Qué imports necesita:
      - `collections.defaultdict`
      - `typing.Any`
      - `resend`
      - `tenacity.retry`, `tenacity.stop_after_attempt`, `tenacity.wait_exponential`, `tenacity.retry_if_exception_type`
      - `app.config.Settings`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def configure_resend(settings: Settings) -> None`
        - Qué hace exactamente: setea `resend.api_key`.
        - Casos de error: API key vacía.
        - Si usa tenacity: no.
      - Firma completa: `def send_novelty_summary(settings: Settings, grouped_by_tag: dict[str, list[dict[str, Any]]]) -> str | None`
        - Qué hace exactamente:
          1) Construye asunto y body HTML/texto.
          2) Agrupa una sola vez por tag en un único email.
          3) Envía a `NOTIFICATION_EMAIL_TO` desde `NOTIFICATION_EMAIL_FROM`.
          4) Si `grouped_by_tag` vacío, retorna `None` y no envía.
        - Casos de error: error API Resend, payload inválido.
        - Si usa tenacity: sí, 3 retries, espera exponencial (1s, 2s, 4s), reintenta en `Exception` de SDK/HTTP.
      - Firma completa: `def send_escalation_email(settings: Settings, author_normalized: str, requests_count: int) -> str | None`
        - Qué hace exactamente: envía alerta de autor desconocido superando umbral.
        - Casos de error: falla Resend.
        - Si usa tenacity: sí, 3 retries, mismas reglas.
      - Firma completa: `def send_error_email(settings: Settings, context: str, error_detail: str) -> str | None`
        - Qué hace exactamente: envía mail técnico para fallos de `/webhook/manual-ingest`.
        - Casos de error: falla Resend.
        - Si usa tenacity: sí, 3 retries, mismas reglas.
- Variables de entorno que consume esta etapa:
  - `RESEND_API_KEY`
  - `NOTIFICATION_EMAIL_TO`
  - `NOTIFICATION_EMAIL_FROM`
  - `ESCALATION_EMAIL_TO`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta: invocar cada función con payload de prueba y confirmar recepción en inbox.
- Dependencias: E1, E2, E3 completas.

---

**Etapa 5 — Scheduler APScheduler**
- Objetivo: programar corrida diaria automática de scraping + detección de novedades y montarla en ciclo de vida de FastAPI.
- Archivos a modificar/completar:
  - app/scheduler.py
  - app/main.py
  - Dockerfile (solo verificar restricción)
- Por cada archivo:
  - app/scheduler.py
    - Qué imports necesita:
      - `logging`
      - `typing.Callable`
      - `apscheduler.schedulers.background.BackgroundScheduler`
      - `apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore`
      - `apscheduler.jobstores.memory.MemoryJobStore`
      - `app.config.Settings`
      - `app.database.get_sqlalchemy_engine`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def build_scheduler(settings: Settings) -> BackgroundScheduler`
        - Qué hace exactamente:
          1) Si existe `SUPABASE_DB_URL`, usa `SQLAlchemyJobStore`.
          2) Si no, fallback `MemoryJobStore`.
          3) Configura timezone UTC.
        - Casos de error: DB URL inválida.
        - Si usa tenacity: no aplica.
      - Firma completa: `def register_scrape_job(scheduler: BackgroundScheduler, settings: Settings, scrape_callable: Callable[[], None]) -> None`
        - Qué hace exactamente: registra job interval diario (`hours=SCRAPE_INTERVAL_HOURS`, default 24), `max_instances=1`, `coalesce=True`.
        - Casos de error: id duplicado o scheduler no inicializado.
        - Si usa tenacity: no aplica.
      - Firma completa: `def start_scheduler(scheduler: BackgroundScheduler) -> None`
      - Firma completa: `def stop_scheduler(scheduler: BackgroundScheduler) -> None`
  - app/main.py
    - Qué imports necesita:
      - `fastapi.FastAPI`
      - imports de routers + scheduler + pipeline
    - Cada función/método que hay que implementar con:
      - Firma completa: `def create_app() -> FastAPI`
        - Qué hace exactamente:
          1) Inyecta `settings`, `supabase`, `scheduler` en `app.state`.
          2) Registra routers.
          3) En startup: registra job y arranca scheduler.
          4) En shutdown: frena scheduler.
        - Casos de error: si scheduler falla, loggear y abortar startup.
        - Si usa tenacity: no aplica.
  - Dockerfile
    - Qué imports necesita: no aplica.
    - Cada función/método que hay que implementar con: no aplica.
    - Verificación requerida: `CMD` debe mantener `--workers 1`.
- Variables de entorno que consume esta etapa:
  - `SUPABASE_DB_URL`
  - `SCRAPE_INTERVAL_HOURS`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - `docker run ...` o ejecución local y revisar logs: debe aparecer registro de job y siguiente run time.
- Dependencias: E1, E2, E3, E4 completas.

---

**Etapa 6 — WhatsApp bot**
- Objetivo: implementar flujo completo de webhook Twilio con validación de firma, parseo de intent, consulta a DB y respuesta TwiML.
- Archivos a modificar/completar:
  - app/services/whatsapp.py
  - app/routers/webhooks.py
- Por cada archivo:
  - app/services/whatsapp.py
    - Qué imports necesita:
      - `re`
      - `dataclasses.dataclass`
      - `enum.Enum`
      - `twilio.twiml.messaging_response.MessagingResponse`
      - `app.services.quotes.count_quotes_by_author`, `app.services.quotes.list_quotes_by_author`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def parse_whatsapp_message(body: str) -> ParsedWhatsAppMessage`
        - Qué hace exactamente:
          1) Normaliza texto de entrada.
          2) Regex COUNT: patrones como `cuantas frases hay de X`.
          3) Regex LIST: patrones como `cuales son de X`.
          4) Si no matchea, intent UNKNOWN.
        - Casos de error: body vacío.
        - Si usa tenacity: no aplica.
      - Firma completa: `def build_count_response(author_query: str, count: int) -> str`
      - Firma completa: `def build_list_response(author_query: str, quotes: list[str]) -> str`
      - Firma completa: `def build_unknown_author_response(author_query: str) -> str`
      - Firma completa: `def build_twiml_response(message: str) -> str`
        - Qué hace exactamente: construye XML TwiML válido con `MessagingResponse`.
        - Casos de error: mensaje vacío.
        - Si usa tenacity: no aplica.
  - app/routers/webhooks.py
    - Qué imports necesita:
      - `fastapi.APIRouter`, `fastapi.Request`, `fastapi.Response`, `fastapi.HTTPException`, `fastapi.status`
      - `twilio.request_validator.RequestValidator`
      - servicios de whatsapp + quotes + escalation
      - `app.config.Settings`
    - Cada función/método que hay que implementar con:
      - Firma completa: `async def whatsapp_webhook(request: Request) -> Response`
        - Qué hace exactamente:
          1) Lee `form-data` (`Body`, `From`).
          2) Valida firma Twilio con header `X-Twilio-Signature` y URL pública del request.
          3) Parsea intent.
          4) Si COUNT: usa `count_quotes_by_author` (ILIKE en `author_slug`).
          5) Si LIST: usa `list_quotes_by_author`.
          6) Si no hay match de autor: registra unknown y dispara evaluación de escalación.
          7) Retorna TwiML XML.
        - Casos de error:
          - firma inválida → 403.
          - payload incompleto → 400.
          - error interno DB/servicio → 500 con mensaje seguro.
        - Si usa tenacity: no aplica.
- Variables de entorno que consume esta etapa:
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta:
    1) Exponer API con URL pública.
    2) Configurar webhook Twilio Sandbox.
    3) Enviar mensajes COUNT y LIST y validar respuestas.
- Dependencias: E2, E3, E4, E5 completas.

---

**Etapa 7 — Escalación de autores desconocidos**
- Objetivo: persistir consultas sin match, aplicar threshold configurable y evitar emails duplicados de escalación.
- Archivos a modificar/completar:
  - app/services/escalation.py
  - app/services/email.py (reutilizar `send_escalation_email`)
- Por cada archivo:
  - app/services/escalation.py
    - Qué imports necesita:
      - `re`
      - `supabase.Client`
      - `app.config.Settings`
      - `app.services.email.send_escalation_email`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def normalize_author_query(author_query: str) -> str`
      - Firma completa: `def register_unknown_author_request(supabase: Client, author_query: str, from_phone: str) -> None`
        - Qué hace exactamente:
          1) Normaliza autor.
          2) Inserta evento en `unknown_author_requests`.
        - Casos de error: insert fallido.
        - Si usa tenacity: no aplica.
      - Firma completa: `def should_escalate_unknown_author(supabase: Client, settings: Settings, author_query: str) -> tuple[bool, int, str]`
        - Qué hace exactamente:
          1) Obtiene `author_normalized`.
          2) Cuenta requests de ese autor.
          3) Verifica si existe algún registro `escalated=True`.
          4) Devuelve `True` solo si count >= threshold y no está escalado.
        - Casos de error: query fallida.
        - Si usa tenacity: no aplica.
      - Firma completa: `def mark_author_as_escalated(supabase: Client, author_normalized: str) -> None`
        - Qué hace exactamente: update masivo de filas de ese autor con `escalated=True`.
        - Casos de error: update fallido.
        - Si usa tenacity: no aplica.
      - Firma completa: `def process_unknown_author_escalation(supabase: Client, settings: Settings, author_query: str) -> bool`
        - Qué hace exactamente:
          1) Evalúa threshold.
          2) Si supera, llama `send_escalation_email`.
          3) Si envío OK, marca `escalated=True`.
          4) Retorna si escaló o no.
        - Casos de error: error email o DB.
        - Si usa tenacity: no (el retry está en email.py).
- Variables de entorno que consume esta etapa:
  - `UNKNOWN_AUTHOR_THRESHOLD` (default 2)
  - `ESCALATION_EMAIL_TO`
  - `RESEND_API_KEY`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta: enviar 2+ consultas de autor inexistente por WhatsApp y verificar mail + `escalated=True` en tabla.
- Dependencias: E4 y E6 completas.

---

**Etapa 8 — Manual ingest**
- Objetivo: procesar webhook de Supabase para filas nuevas en `manual_queue`, validar datos y cargar idempotente en `quotes`.
- Archivos a modificar/completar:
  - app/routers/webhooks.py
  - app/services/quotes.py
  - app/services/email.py
- Por cada archivo:
  - app/routers/webhooks.py
    - Qué imports necesita:
      - `fastapi.Header`, `fastapi.HTTPException`, `fastapi.status`
      - `app.models.schemas.ManualIngestWebhookPayload`
      - servicios de quotes y email
    - Cada función/método que hay que implementar con:
      - Firma completa: `def manual_ingest_webhook(payload: dict, x_webhook_secret: str | None = Header(default=None, alias='X-Webhook-Secret')) -> GenericWebhookResponse`
        - Qué hace exactamente:
          1) Valida secret (`WEBHOOK_SECRET`).
          2) Extrae `record` del payload (`text`, `author`, `tags`, `id`).
          3) Valida `text` y `author` obligatorios.
          4) Llama `upsert_quote_manual`.
          5) Si éxito: update `manual_queue.status='approved'`, `processed_at=now`.
          6) Si error: update `manual_queue.status='error'`, `error_detail` y enviar `send_error_email`.
        - Casos de error:
          - secret inválido → 401.
          - payload inválido → 400.
          - fallo DB/email → 500.
        - Si usa tenacity: no en router.
  - app/services/quotes.py
    - Qué imports necesita:
      - helpers hash/author del ingestor
    - Cada función/método que hay que implementar con:
      - Firma completa: `def upsert_quote_manual(supabase: Client, text: str, author: str, tags: list[str]) -> dict[str, Any]`
        - (ya definida en E2; usar en esta etapa).
  - app/services/email.py
    - Qué imports necesita:
      - (ya definidos en E4)
    - Cada función/método que hay que implementar con:
      - Firma completa: `def send_error_email(settings: Settings, context: str, error_detail: str) -> str | None`
        - (ya definida en E4; usar en esta etapa).
- Variables de entorno que consume esta etapa:
  - `WEBHOOK_SECRET`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `RESEND_API_KEY`
  - `NOTIFICATION_EMAIL_FROM`
  - `NOTIFICATION_EMAIL_TO`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Acción exacta:
    1) Insertar fila en `manual_queue` con `status='pending'`.
    2) Disparar webhook (desde Supabase).
    3) Verificar insert/upsert en `quotes` y cambio de estado en `manual_queue`.
- Dependencias: E2, E3, E4 completas.

Pasos exactos para configurar webhook en Supabase Dashboard:
1) Ir a Database > Webhooks.
2) Click en Create a new webhook.
3) Tabla: `public.manual_queue`.
4) Eventos: `INSERT`.
5) URL: `https://<railway-domain>/webhook/manual-ingest`.
6) Method: `POST`.
7) Headers: agregar `X-Webhook-Secret: <WEBHOOK_SECRET>`.
8) Guardar y ejecutar test webhook desde el panel.

---

**Etapa 9 — Admin Streamlit**
- Objetivo: panel operativo para administrar tags/quotes y disparar scraping manual con autenticación básica.
- Archivos a modificar/completar:
  - admin/app.py
  - admin/pages/1_Tags.py (crear)
  - admin/pages/2_Quotes.py (crear)
- Por cada archivo:
  - admin/app.py
    - Qué imports necesita:
      - `os`
      - `requests`
      - `streamlit as st`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def require_auth() -> None`
        - Qué hace exactamente:
          1) Lee `st.secrets['ADMIN_USER']` y `st.secrets['ADMIN_PASSWORD']`.
          2) Muestra login form.
          3) Guarda sesión autenticada en `st.session_state`.
        - Casos de error: secretos faltantes, credenciales inválidas.
        - Si usa tenacity: no aplica.
      - Firma completa: `def get_api_base_url() -> str`
      - Firma completa: `def render_scrape_trigger_section(api_base_url: str) -> None`
        - Qué hace exactamente: botón `Correr scraping ahora` y POST a `/trigger/scrape`.
        - Casos de error: backend caído, timeout, status != 200.
        - Si usa tenacity: no.
  - admin/pages/1_Tags.py
    - Qué imports necesita:
      - `requests`
      - `streamlit as st`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def fetch_tags(api_base_url: str) -> list[dict]`
      - Firma completa: `def toggle_tag(api_base_url: str, tag_id: str, active: bool) -> None`
      - Firma completa: `def create_tag(api_base_url: str, tag: str) -> None`
      - Firma completa: `def delete_tag(api_base_url: str, tag_id: str) -> None`
        - Qué hacen exactamente: CRUD completo sobre `monitored_tags` con UI de tabla + acciones.
        - Casos de error: conexión, validación de tag vacío, duplicado.
        - Si usa tenacity: no.
  - admin/pages/2_Quotes.py
    - Qué imports necesita:
      - `requests`
      - `streamlit as st`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def fetch_quotes(api_base_url: str, author_filter: str | None, page: int, page_size: int) -> list[dict]`
      - Firma completa: `def toggle_quote(api_base_url: str, quote_id: str, active: bool) -> None`
        - Qué hacen exactamente: tabla paginada, filtro por autor, toggle active/inactive.
        - Casos de error: conexión, página inválida.
        - Si usa tenacity: no.
- Variables de entorno que consume esta etapa:
  - `FASTAPI_BASE_URL`
  - Streamlit secrets: `ADMIN_USER`, `ADMIN_PASSWORD`
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - `streamlit run admin/app.py --server.port 8501`
  - Acción exacta: login, crear tag, togglear tag, togglear quote, disparar scraping.
- Dependencias: E2, E3 completas.

---

**Etapa 10 — Tests**
- Objetivo: asegurar comportamiento crítico de scraper, ingesta idempotente y bot WhatsApp.
- Archivos a modificar/completar:
  - tests/test_scraper.py
  - tests/test_whatsapp.py
  - tests/test_ingestor.py
  - tests/conftest.py (si hace falta fixtures extra)
- Por cada archivo:
  - tests/test_scraper.py
    - Qué imports necesita:
      - `pytest`
      - `unittest.mock.patch`, `unittest.mock.Mock`
      - funciones de `app.scraper.session` y `app.scraper.crawler`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def test_login_with_csrf_success(...) -> None`
      - Firma completa: `def test_login_with_csrf_missing_token_raises(...) -> None`
      - Firma completa: `def test_crawl_all_quotes_follows_pagination_until_end(...) -> None`
        - Qué mockear: `requests.Session.get/post`.
        - Casos de error cubiertos: token faltante, error HTTP.
  - tests/test_whatsapp.py
    - Qué imports necesita:
      - `pytest`
      - `app.services.whatsapp.*`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def test_parse_intent_count(...) -> None`
      - Firma completa: `def test_parse_intent_list(...) -> None`
      - Firma completa: `def test_parse_intent_unknown(...) -> None`
        - Qué mockear: no necesario para parse puro.
  - tests/test_ingestor.py
    - Qué imports necesita:
      - `pytest`
      - `unittest.mock.Mock`
      - funciones de `app.scraper.ingestor`
    - Cada función/método que hay que implementar con:
      - Firma completa: `def test_normalize_text_same_hash_for_equivalent_inputs(...) -> None`
      - Firma completa: `def test_upsert_quotes_idempotent_ignores_duplicates(...) -> None`
      - Firma completa: `def test_record_scrape_run_persists_metrics(...) -> None`
        - Qué mockear: cliente `supabase` (`table().insert().execute()` chain).
- Variables de entorno que consume esta etapa:
  - usar fixtures dummy en tests (`tests/conftest.py`).
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - `pytest -q`
- Dependencias: E1, E2, E3, E6 completas.

---

**Etapa 11 — Deploy**
- Objetivo: desplegar API y admin, conectar webhooks (Supabase y Twilio) y validar operación E2E.
- Archivos a modificar/completar:
  - Dockerfile (verificación final)
  - README.md (si falta reflejar deploy final)
- Por cada archivo:
  - Dockerfile
    - Qué imports necesita: no aplica.
    - Cada función/método que hay que implementar con: no aplica.
    - Verificar:
      - `CMD` con `uvicorn ... --workers 1`.
      - `EXPOSE 8000`.
  - README.md
    - Qué imports necesita: no aplica.
    - Qué completar: URLs finales, pasos reales de deploy y troubleshooting.
- Variables de entorno que consume esta etapa:
  - todas las de `.env.example`.
- Cómo verificar que la etapa funciona (comando exacto o acción exacta):
  - Railway:
    1) Crear proyecto nuevo > Deploy from GitHub.
    2) Root directory: repositorio raíz.
    3) Builder: Dockerfile detectado automáticamente (path `./Dockerfile`).
    4) Variables en Railway: cargar todas las de `.env.example`.
    5) Deploy y probar `GET /health`.
  - Streamlit Cloud:
    1) New app > seleccionar repo/branch.
    2) Main file path: `admin/app.py`.
    3) En Settings > Secrets, cargar `FASTAPI_BASE_URL`, `ADMIN_USER`, `ADMIN_PASSWORD` (y opcionalmente Supabase keys si el panel las usa directo).
    4) Deploy y abrir URL del panel.
  - Supabase DB Webhook a Railway:
    1) Database > Webhooks > Create.
    2) Table `manual_queue`, event `INSERT`.
    3) URL `https://<railway-domain>/webhook/manual-ingest`.
    4) Header `X-Webhook-Secret`.
  - Twilio Sandbox a Railway:
    1) Console Twilio > Messaging > Try it out > WhatsApp Sandbox.
    2) En “When a message comes in”, setear `https://<railway-domain>/webhook/whatsapp`.
    3) Method `HTTP POST`.
    4) Guardar.
- Dependencias: E1 a E10 completas.

Checklist de verificación post-deploy (mínimo 5 checks):
1) `GET /health` devuelve `status=ok`, timestamp UTC y versión.
2) `POST /trigger/scrape` devuelve `ScrapeResult` con métricas > 0 en primera corrida.
3) Segunda corrida no incrementa duplicados en `quotes` (idempotencia válida).
4) WhatsApp COUNT/LIST responde TwiML correcto con datos reales de Supabase.
5) Autor desconocido repetido 2+ veces dispara 1 solo email de escalación.
6) Insert en `manual_queue` dispara ingest y actualiza estado a `approved` o `error`.
7) Streamlit permite togglear `active` en tags y frases sin errores.

---

## Contexto del proyecto para el agente nuevo

- Stack completo y por qué se eligió cada pieza:
  - FastAPI: API/webhooks/scheduler hooks en un solo servicio, legible y testeable.
  - APScheduler: reemplaza trigger visual; job diario con control explícito.
  - Supabase PostgreSQL: storage estructurado, idempotencia robusta, operación simple.
  - Streamlit: panel admin rápido para operación interna.
  - Twilio Sandbox: canal WhatsApp free para demo funcional.
  - Resend: emails de novedades/escalación/error con SDK simple.

- Decisiones de diseño no obvias:
  - `text_hash` (SHA-256 sobre texto normalizado) como clave de idempotencia en vez de UNIQUE sobre `text` raw.
  - `author_slug` normalizado para búsquedas flexibles (`ILIKE`) en consultas del bot.
  - `--workers 1` obligatorio mientras APScheduler corre dentro del proceso FastAPI.
  - No crear endpoint separado `/webhook/escalate`; la escalación se dispara desde flujo de WhatsApp.
  - Scraping de una sola pasada por paginación completa; filtrado de tags en memoria.

- Proyecto Supabase ID y tablas existentes con su estado actual:
  - ID objetivo indicado por negocio: `buriiwhtcgxlrksbhkqo`.
  - Estado actual verificado en entorno MCP conectado: tablas `quotes`, `monitored_tags`, `unknown_author_requests`, `manual_queue`, `scrape_runs` creadas.
  - Conteos observados en la verificación inicial:
    - `quotes`: 0
    - `monitored_tags`: 4 (seed: love, humor, life, inspirational)
    - `unknown_author_requests`: 0
    - `manual_queue`: 0
    - `scrape_runs`: 0

- Archivos que ya existen como skeletons (listos para implementar):
  - app/main.py
  - app/config.py
  - app/database.py
  - app/scheduler.py
  - app/scraper/session.py
  - app/scraper/crawler.py
  - app/scraper/ingestor.py
  - app/services/quotes.py
  - app/services/tags.py
  - app/services/whatsapp.py
  - app/services/email.py
  - app/services/escalation.py
  - app/routers/health.py
  - app/routers/trigger.py
  - app/routers/webhooks.py
  - app/models/schemas.py
  - admin/app.py
  - tests/test_scraper.py
  - tests/test_whatsapp.py
  - tests/test_ingestor.py

- Lo que NO hacer:
  - No agregar n8n ni plantearlo como alternativa.
  - No crear endpoint `/webhook/escalate` separado.
  - No hardcodear credenciales (scraping, Supabase, Twilio, Resend).
  - No cambiar `--workers 1` mientras APScheduler esté embebido.

- Variables de entorno requeridas con descripción:
  - `SUPABASE_URL`: URL del proyecto Supabase.
  - `SUPABASE_ANON_KEY`: clave pública (uso limitado).
  - `SUPABASE_SERVICE_ROLE_KEY`: clave backend con privilegios.
  - `SUPABASE_DB_URL`: cadena Postgres para `SQLAlchemyJobStore`.
  - `SCRAPE_BASE_URL`: base del sitio a scrapear (`quotes.toscrape.com`).
  - `SCRAPE_USERNAME`: usuario de login del scraper.
  - `SCRAPE_PASSWORD`: contraseña de login del scraper.
  - `SCRAPE_INTERVAL_HOURS`: intervalo del job automático.
  - `TWILIO_ACCOUNT_SID`: SID de cuenta Twilio.
  - `TWILIO_AUTH_TOKEN`: token para validar firma y SDK.
  - `TWILIO_WHATSAPP_FROM`: remitente sandbox WhatsApp.
  - `RESEND_API_KEY`: API key de Resend.
  - `NOTIFICATION_EMAIL_TO`: destinatario de resumen de novedades.
  - `NOTIFICATION_EMAIL_FROM`: remitente autorizado.
  - `ESCALATION_EMAIL_TO`: destinatario de escalaciones.
  - `UNKNOWN_AUTHOR_THRESHOLD`: umbral de consultas para escalar (default 2).
  - `WEBHOOK_SECRET`: secreto compartido para `/webhook/manual-ingest`.
  - `FASTAPI_BASE_URL`: URL base usada por panel Streamlit.
