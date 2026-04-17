# Job Scout Assistant

Job Scout Assistant descubre vacantes desde Greenhouse, las filtra por palabras clave, elimina duplicados, las puntúa con reglas configurables, las guarda en SQLite y envía alertas relevantes por Discord.

Sprint 3 agrega una capa opcional de CV maestro basada en PDF:

- toma `data/resumes/master_resume.pdf`
- extrae su texto
- construye `data/resumes/master_resume.json`
- usa ese perfil estructurado para tailoring por vacante
- genera outputs en Markdown, metadata JSON y, si la dependencia está disponible, también un PDF simple del CV adaptado

## Estructura

- `app/`: punto de entrada y orquestación
- `core/`: configuración, logging y modelos
- `sources/`: fuentes de vacantes
- `pipeline/`: descubrimiento, deduplicación, filtrado y scoring
- `storage/`: SQLite y repositorios
- `notifications/`: envío a Discord
- `tailoring/`: parsing del PDF, perfil maestro estructurado, tailoring y exportación de outputs

## Instalación

Requiere Python 3.11 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencias nuevas del Sprint 3:

- `pypdf`: extracción de texto desde PDFs con capa de texto
- `reportlab`: exportación simple y estable del CV adaptado a PDF

## Configuración

Crea un archivo `.env` en la raíz del proyecto.

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DATABASE_PATH=data/jobs.db
INCLUDE_KEYWORDS=python,backend,api
EXCLUDE_KEYWORDS=intern,frontend
SCORING_ENABLED=true
SCORING_MIN_NOTIFY_SCORE=60
PREFERRED_KEYWORDS=python,backend,api
PREFERRED_LOCATIONS=remote,mexico
SENIORITY_PREFERENCE=senior
GREENHOUSE_ENABLED=true
GREENHOUSE_COMPANY_BOARDS=empresa-a,empresa-b
GREENHOUSE_INCLUDE_CONTENT=true
REQUEST_TIMEOUT_SECONDS=20
LOG_LEVEL=INFO
```

## Scoring

- El scoring es interpretable y basado en reglas, sin LLMs.
- Analiza `title`, `description`, `company`, `location` y `normalized_tags`.
- Produce `score` de 0 a 100, `score_label` y una lista corta de razones legibles.
- `SCORING_MIN_NOTIFY_SCORE` define el umbral mínimo para notificar una vacante relevante.

## Ejecución

La forma oficial de correr el proyecto es:

```bash
python -m app
```

Si tu entorno solo expone `python3`, usa `python3 -m app`. No uses `python app/main.py`; el entrypoint soportado es el módulo `app`.

## Uso básico

- Configura al menos un board en `GREENHOUSE_COMPANY_BOARDS`.
- Las vacantes nuevas se guardan en SQLite.
- Solo las vacantes nuevas, relevantes y con score suficiente se notifican por Discord.
- La deduplicación se hace contra el batch actual y contra la base de datos.

## CV Maestro Basado En PDF

Flujo:

```text
data/resumes/master_resume.pdf
-> extracción/parsing
-> data/resumes/master_resume.json
-> tailoring por vacante
-> data/outputs/
```

Archivos relevantes:

- PDF fuente humana: `data/resumes/master_resume.pdf`
- Perfil estructurado reutilizable: `data/resumes/master_resume.json`
- Ejemplo de estructura: `data/resumes/master_resume.example.json`
- Outputs finales: `data/outputs/`

El tailoring trabaja sobre `master_resume.json`, no sobre el PDF bruto en cada ejecución.

### Generar El Perfil Maestro Desde El PDF

Coloca tu CV real en:

```text
data/resumes/master_resume.pdf
```

Luego ejecuta:

```bash
python -m tailoring.build_master_profile
```

Si tu entorno solo expone `python3`:

```bash
python3 -m tailoring.build_master_profile
```

También puedes personalizar rutas:

```bash
python -m tailoring.build_master_profile \
  --input-pdf data/resumes/master_resume.pdf \
  --output-json data/resumes/master_resume.json
```

Qué hace:

- extrae texto del PDF
- intenta detectar secciones como `summary`, `skills`, `experience`, `projects`, `education`, `certifications` y `languages`
- guarda un perfil maestro estructurado y tipado en JSON
- emite warnings si la extracción sale pobre o incompleta

Limitaciones reales de esta versión:

- funciona mejor cuando el PDF tiene texto seleccionable
- no implementa OCR
- si el PDF es una imagen escaneada o tiene mala capa de texto, la extracción puede salir incompleta y conviene revisar manualmente `master_resume.json`

## Tailoring Por Vacante

Entry points soportados:

```bash
python -m tailoring
python -m tailoring.generate_tailored_resume
```

Por defecto:

- carga `data/resumes/master_resume.json`
- toma la vacante con mejor score reciente desde SQLite
- genera outputs en `data/outputs/`

Comando básico:

```bash
python -m tailoring
```

Usando una vacante concreta:

```bash
python -m tailoring.generate_tailored_resume --job-id 756
```

Usando un perfil JSON explícito:

```bash
python -m tailoring.generate_tailored_resume --profile data/resumes/master_resume.json
```

Si quieres omitir el PDF final:

```bash
python -m tailoring.generate_tailored_resume --skip-pdf
```

## Outputs Generados

Para cada vacante se generan archivos con nombre sanitizado:

```text
data/outputs/company__role__job-123__resume.md
data/outputs/company__role__job-123__summary.md
data/outputs/company__role__job-123__metadata.json
data/outputs/company__role__job-123__resume.pdf
```

Contenido:

- `resume.md`: CV adaptado para la vacante
- `summary.md`: resumen de ajuste y gaps
- `metadata.json`: señales usadas, priorización y warnings de exportación
- `resume.pdf`: versión simple, estable y ATS-friendly del CV adaptado

## Exportación A PDF

La exportación del CV adaptado a PDF usa `reportlab`.

Características del PDF:

- layout simple
- sin diseño complejo
- prioriza claridad, estabilidad y utilidad práctica

Si `reportlab` no está instalado en el entorno actual:

- el sistema sigue generando Markdown y metadata JSON
- el warning queda registrado en `metadata.json`
- no se rompe el resto del flujo
