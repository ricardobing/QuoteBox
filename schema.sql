-- ============================================================
-- QuoteBox — Schema SQL completo
-- Ejecutar contra el proyecto Supabase via MCP o CLI.
-- Ya fue aplicado via migration: quotebox_initial_schema
-- ============================================================

-- 1. quotes: frases scrapeadas o cargadas manualmente
-- ============================================================
CREATE TABLE IF NOT EXISTS public.quotes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    text            TEXT        NOT NULL,
    -- SHA-256 del texto normalizado (lowercase + whitespace colapsado).
    -- Clave de idempotencia: ON CONFLICT (text_hash) DO NOTHING.
    -- Usar hash evita el límite de btree sobre TEXT largo y variaciones de encoding.
    text_hash       CHAR(64)    NOT NULL,
    author          TEXT        NOT NULL,
    -- Versión lowercase+stripped del author para búsquedas ILIKE eficientes.
    author_slug     TEXT        NOT NULL,
    tags            TEXT[]      NOT NULL    DEFAULT '{}',
    source          TEXT        NOT NULL    DEFAULT 'scraper'
                                CHECK (source IN ('scraper', 'manual')),
    active          BOOLEAN     NOT NULL    DEFAULT TRUE,
    first_seen_at   TIMESTAMPTZ NOT NULL    DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL    DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL    DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_quotes_text_hash  ON public.quotes (text_hash);
CREATE INDEX        IF NOT EXISTS idx_quotes_author     ON public.quotes (author_slug);
CREATE INDEX        IF NOT EXISTS idx_quotes_tags       ON public.quotes USING GIN (tags);
CREATE INDEX        IF NOT EXISTS idx_quotes_active     ON public.quotes (active);

ALTER TABLE public.quotes ENABLE ROW LEVEL SECURITY;
-- El backend usa service_role_key (bypasea RLS).
-- Sin políticas explícitas, anon no tiene acceso.

-- 2. monitored_tags: lista de tags activos que el scraper monitorea
-- ============================================================
CREATE TABLE IF NOT EXISTS public.monitored_tags (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tag         TEXT        NOT NULL,
    active      BOOLEAN     NOT NULL    DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL    DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL    DEFAULT NOW()
);

-- UNIQUE sobre lower(tag) previene duplicados case-insensitive
CREATE UNIQUE INDEX IF NOT EXISTS uq_monitored_tags_tag ON public.monitored_tags (lower(tag));

ALTER TABLE public.monitored_tags ENABLE ROW LEVEL SECURITY;

-- Seed: tags iniciales
INSERT INTO public.monitored_tags (tag, active)
VALUES
    ('love',          true),
    ('humor',         true),
    ('life',          true),
    ('inspirational', true)
ON CONFLICT DO NOTHING;

-- 3. unknown_author_requests: consultas WA para autores no encontrados
-- ============================================================
CREATE TABLE IF NOT EXISTS public.unknown_author_requests (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    author_query        TEXT        NOT NULL,   -- texto original del usuario
    author_normalized   TEXT        NOT NULL,   -- lowercase + trim
    from_phone          TEXT        NOT NULL,
    escalated           BOOLEAN     NOT NULL    DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uar_author_norm ON public.unknown_author_requests (author_normalized);
CREATE INDEX IF NOT EXISTS idx_uar_escalated   ON public.unknown_author_requests (author_normalized, escalated);

ALTER TABLE public.unknown_author_requests ENABLE ROW LEVEL SECURITY;

-- 4. manual_queue: staging para carga manual por el equipo
-- ============================================================
CREATE TABLE IF NOT EXISTS public.manual_queue (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    text            TEXT        NOT NULL,
    author          TEXT        NOT NULL,
    tags            TEXT[]      NOT NULL    DEFAULT '{}',
    submitted_by    TEXT,
    status          TEXT        NOT NULL    DEFAULT 'pending'
                                CHECK (status IN ('pending', 'approved', 'rejected', 'error')),
    error_detail    TEXT,
    created_at      TIMESTAMPTZ NOT NULL    DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);

ALTER TABLE public.manual_queue ENABLE ROW LEVEL SECURITY;

-- 5. scrape_runs: log de auditoría de cada corrida del scraper
-- ============================================================
CREATE TABLE IF NOT EXISTS public.scrape_runs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at      TIMESTAMPTZ NOT NULL    DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL    DEFAULT 'running'
                                CHECK (status IN ('running', 'success', 'error', 'partial')),
    pages_scraped   INTEGER     NOT NULL    DEFAULT 0,
    quotes_found    INTEGER     NOT NULL    DEFAULT 0,
    quotes_new      INTEGER     NOT NULL    DEFAULT 0,
    error_detail    TEXT
);

ALTER TABLE public.scrape_runs ENABLE ROW LEVEL SECURITY;
