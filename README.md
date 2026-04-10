# Job Scout Assistant

Job Scout Assistant descubre vacantes desde Greenhouse, las filtra por palabras clave, elimina duplicados, las puntúa con reglas configurables, las guarda en SQLite y envía alertas relevantes por Discord.

## Estructura

- `app/`: punto de entrada y orquestación
- `core/`: configuración, logging y modelos
- `sources/`: fuentes de vacantes
- `pipeline/`: descubrimiento, deduplicación, filtrado y scoring
- `storage/`: SQLite y repositorios
- `notifications/`: envío a Discord

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
