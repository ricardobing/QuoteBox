# Guía de pruebas — QuoteBox

URL producción: `https://quotebox-production-43dc.up.railway.app`

---

## 1. Scraping con login

### 1.1 Verificar credenciales no hardcodeadas
```bash
# Las credenciales están en variables de entorno, no en el código.
# Verificá en Railway Dashboard > QuoteBox > Variables:
# SCRAPE_USERNAME, SCRAPE_PASSWORD existen y no se ven en app/config.py
grep -r "ArchytasUser" app/      # no debe aparecer
grep -r "SCRAPE_PASSWORD" app/   # solo en config.py como alias
```

### 1.2 Disparar scraping manual
```bash
curl -X POST https://quotebox-production-43dc.up.railway.app/trigger/scrape
# Respuesta esperada:
# {"status":"success","pages_scraped":10,"quotes_found":100,"quotes_new":0}
```
> quotes_new=0 confirma que ya están todas cargadas. La primera vez fue >0.

### 1.3 Verificar paginación dinámica
```bash
# El crawler recorre todas las páginas siguiendo li.next a[href].
# No hay límite hardcodeado. Ver en:
# app/scraper/crawler.py líneas 67-89
# while page_url: ... next_link = soup.select_one("li.next a")
```

---

## 2. Storage e idempotencia

### 2.1 Verificar estructura
```sql
-- En Supabase Dashboard > SQL Editor:
SELECT COUNT(*) FROM quotes;          -- ~50 frases
SELECT * FROM quotes LIMIT 1;         -- text, author, tags, text_hash, author_slug, source, active
```

### 2.2 Probar idempotencia
```bash
# Paso 1: contar frases
SELECT COUNT(*) FROM quotes;  -- anotá el número

# Paso 2: correr scrape de nuevo
curl -X POST https://quotebox-production-43dc.up.railway.app/trigger/scrape
# quotes_new debe ser 0

# Paso 3: verificar que el count no cambió
SELECT COUNT(*) FROM quotes;  -- mismo número
```

### 2.3 Verificar text_hash único
```sql
SELECT text_hash, COUNT(*) FROM quotes GROUP BY text_hash HAVING COUNT(*) > 1;
-- Debe retornar 0 filas (sin duplicados)
```

---

## 3. Detección de novedades

### 3.1 Agregar tag nuevo
```bash
# Desde Supabase SQL Editor:
INSERT INTO monitored_tags (tag, active) VALUES ('change', true);

# Disparar scrape:
curl -X POST https://quotebox-production-43dc.up.railway.app/trigger/scrape
# quotes_new debería ser > 0 (detectó frases con el tag nuevo)

# Verificar quote nueva:
SELECT text, author, tags FROM quotes WHERE 'change' = ANY(tags);

# Limpiar:
DELETE FROM monitored_tags WHERE tag = 'change';
```

### 3.2 Verificar mail de novedades (manual)
1. Agregá el tag `change` desde el panel Streamlit (página Tags)
2. `POST /trigger/scrape`
3. Revisá `ricardobingeniero@gmail.com` — debe haber llegado un mail con asunto "QuoteBox — N frases nuevas detectadas"

### 3.3 Desactivar frase
```sql
-- Tomar una quote:
SELECT id, text, active FROM quotes WHERE active = true LIMIT 1;

-- Desactivarla:
UPDATE quotes SET active = false WHERE id = '<id_copiado>';

-- Correr scrape:
curl -X POST https://quotebox-production-43dc.up.railway.app/trigger/scrape

-- Verificar que sigue inactiva:
SELECT active FROM quotes WHERE id = '<id_copiado>';
-- Debe seguir en false
```

### 3.4 Eliminar frase → vuelve como novedad
```sql
-- Eliminar la quote desactivada:
DELETE FROM quotes WHERE id = '<id_copiado>';

-- Correr scrape:
curl -X POST https://quotebox-production-43dc.up.railway.app/trigger/scrape
-- quotes_new debe ser >= 1 (la quote reinsertada)
```

---

## 4. Bot de WhatsApp

### 4.1 Probar COUNT
Mandá desde WhatsApp al `+1 415 523 8886`:
```
cuantas frases hay de Einstein
```
Esperado: `Hay 2 frases de einstein.`

### 4.2 Probar LIST
```
frases de Bob Marley
```
Esperado: lista numerada con las frases de Bob Marley.

### 4.3 Probar conversación contextual
```
cuantas frases hay de Einstein
→ "Hay 2 frases de einstein."
cuales son?
→ Debería listar las frases de Einstein (recuerda el autor de la conversación)
```

### 4.4 Probar variantes
```
cuantas frases hay en Einstein          → COUNT (preposición "en")
cuantas tiene Oscar Wilde               → COUNT
Cuántas frases hay de Einstein?         → COUNT (signos limpios)
FRASES DE EINSTEIN                      → LIST (case insensitive)
dame frases de Neruda                   → LIST
hola                                    → UNKNOWN (mensaje de ayuda)
```

---

## 5. Autores desconocidos y escalación

### 5.1 Registrar autor desconocido
```
frases de TestAutorUnico2026
```
Esperado: `No tenemos frases de testautorunico2026 por ahora. Ya registre tu solicitud.`

### 5.2 Verificar registro en DB
```sql
SELECT * FROM unknown_author_requests WHERE author_normalized = 'testautorunico2026';
-- Debe haber 1 fila, escalated=false
```

### 5.3 Disparar escalación (2da consulta)
Mandar de nuevo:
```
frases de TestAutorUnico2026
```
- Revisar `ricardobingeniero@gmail.com` — debe llegar mail de escalación
- Verificar DB:
```sql
SELECT * FROM unknown_author_requests WHERE author_normalized = 'testautorunico2026';
-- escalated debe ser true
```

### 5.4 Tercera consulta NO reenvía
Mandar una tercera vez — NO debe llegar otro mail de escalación.

---

## 6. Carga manual

### 6.1 Desde el panel Streamlit
1. Entrar a https://quotebox-admin.streamlit.app (o URL del deploy)
2. Contraseña: `admin123`
3. Ir a página "Carga Manual"
4. Ingresar:
   - Frase: `La paciencia es un árbol de raíz amarga pero de frutos muy dulces.`
   - Autor: `Proverbio Persa`
   - Tags: `life, humor`
5. Botón "Cargar frase" → debe mostrar éxito

### 6.2 Verificar en DB
```sql
SELECT * FROM quotes WHERE author = 'Proverbio Persa';
-- Debe aparecer con source='manual'
```

### 6.3 Verificar duplicado
Cargar la misma frase de nuevo → debe mostrar warning "Esta frase ya existe en el storage."

### 6.4 Probar desde WhatsApp
```
frases de Proverbio Persa
```
Debe responder con la frase cargada manualmente (igual que las scrapeadas).

### 6.5 Carga manual vía DB webhook (Supabase)
```sql
INSERT INTO manual_queue (text, author, tags, status) 
VALUES ('El conocimiento habla, la sabiduría escucha.', 'Jimi Hendrix', ARRAY['life'], 'pending');
-- Esperar 5 segundos, luego:
SELECT * FROM quotes WHERE text LIKE '%conocimiento habla%';
-- Debe aparecer con source='manual'
SELECT status FROM manual_queue WHERE text LIKE '%conocimiento habla%';
-- Debe ser 'approved'
```

---

## 7. Panel admin

| Página | Verificar |
|--------|-----------|
| **Home** | 3 métricas visibles, botón "Correr scraping ahora" funciona |
| **Tags** | 4 tags (love, humor, life, inspirational), toggle activo/inactivo, agregar/eliminar |
| **Quotes** | Tabla paginada, filtro por autor, filtro por tag, toggle activo/inactivo por fila |
| **Carga Manual** | Formulario funcional, tabla de frases manuales debajo |

---

## 8. Tests automáticos

```bash
# Suite completa (91 tests)
cd QuoteBox
pytest tests/ -q                    # 30 tests unitarios
python tests/qa_full.py              # 51 tests contra Railway + Supabase
python tests/qa_streamlit_backend.py # 10 tests de endpoints admin
```

---

## 9. Pruebas extra (lo que podría pedir el cliente)

### 9.1 Simular caída del sitio
El scraper maneja errores HTTP con mensajes claros. Si el sitio no responde, el scrape_run queda con status='error' y detalle del fallo.

### 9.2 Agregar tag con espacio o mayúsculas
```sql
INSERT INTO monitored_tags (tag, active) VALUES ('  Humor  ', true);
-- El índice UNIQUE sobre lower(tag) lo normaliza automáticamente.
-- Verificar: SELECT * FROM monitored_tags WHERE tag = 'humor';
```

### 9.3 Pico de consultas WhatsApp
El bot responde con datos indexados por `author_slug`. Soportaría más volumen sin reescribir.

### 9.4 Verificar logs de Railway
Entrar a Railway Dashboard → QuoteBox → Deployments → Logs. Ver que cada scrape registra métricas.

### 9.5 Verificar secrets no expuestos
```bash
grep -r "eyJhbGci" app/            # no debe aparecer (claves en .env)
grep -r "re_iZoFsFrt" app/         # no debe aparecer
```
