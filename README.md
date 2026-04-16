# Job Scout Assistant

Job Scout Assistant descubre vacantes desde Greenhouse, las filtra por palabras clave, elimina duplicados, las puntúa con reglas configurables, las guarda en SQLite y envía alertas relevantes por Discord.

Sprint 3 agrega una capa opcional de tailoring de CV: toma una vacante ya guardada en SQLite, carga un CV maestro estructurado desde archivo local y genera un CV adaptado en Markdown, un resumen de ajuste y metadata JSON. No hace auto-apply, no usa frontend y no requiere LLMs.

## Estructura

- `app/`: punto de entrada y orquestación
- `core/`: configuración, logging y modelos
- `sources/`: fuentes de vacantes
- `pipeline/`: descubrimiento, deduplicación, filtrado y scoring
- `storage/`: SQLite y repositorios
- `notifications/`: envío a Discord
- `tailoring/`: carga del CV maestro, tailoring por vacante y exportación de outputs

## Instalación

Requiere Python 3.11 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

## CV maestro

El tailoring usa un CV maestro estructurado en JSON.

- Ruta esperada: `data/resumes/master_resume.json`
- Ejemplo base: `data/resumes/master_resume.example.json`
- Salidas generadas: `data/outputs/`

Si aún no tienes tu archivo real, crea `data/resumes/master_resume.json` a partir del example y reemplaza los placeholders con datos verificables tuyos.

Estructura soportada del CV maestro:

- `basics`
- `summary`
- `skills`
- `experience`
- `projects`
- `education`
- `certifications`
- `languages`

Restricción importante: el tailoring solo reordena, prioriza y reformula ligeramente contenido ya presente en el CV maestro. No inventa experiencia, skills ni logros.

## Tailoring

El entrypoint nuevo es independiente del flujo principal y no ensucia `python -m app`.

Comando por defecto:

```bash
python -m tailoring
```

Si tu entorno solo expone `python3`:

```bash
python3 -m tailoring
```

Comportamiento:

- Carga `data/resumes/master_resume.json`
- Toma la mejor vacante reciente desde SQLite
- Genera un CV adaptado `.md`
- Genera un resumen de ajuste `.md`
- Genera metadata `.json`
- Guarda todo en `data/outputs/`

También puedes apuntar a una vacante concreta por ID:

```bash
python -m tailoring --job-id 725
```

Opciones útiles:

```bash
python -m tailoring --resume data/resumes/master_resume.json --output-dir data/outputs
```

Los nombres de archivo se sanitizan para filesystem y quedan con formato similar a:

```text
data/outputs/airbnb__senior-machine-learning-engineer-payments__job-725__resume.md
data/outputs/airbnb__senior-machine-learning-engineer-payments__job-725__summary.md
data/outputs/airbnb__senior-machine-learning-engineer-payments__job-725__metadata.json
```
