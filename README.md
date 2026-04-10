# Job Scout Assistant

Job Scout Assistant descubre vacantes desde Greenhouse, las filtra por palabras clave, elimina duplicados, las guarda en SQLite y envía alertas relevantes por Discord.

## Estructura

- `app/`: punto de entrada y orquestación
- `core/`: configuración, logging y modelos
- `sources/`: fuentes de vacantes
- `pipeline/`: descubrimiento, deduplicación y filtrado
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
GREENHOUSE_ENABLED=true
GREENHOUSE_COMPANY_BOARDS=empresa-a,empresa-b
GREENHOUSE_INCLUDE_CONTENT=true
INCLUDE_KEYWORDS=python,backend,api
EXCLUDE_KEYWORDS=intern,frontend
REQUEST_TIMEOUT_SECONDS=20
LOG_LEVEL=INFO
```

## Ejecución

La forma oficial de correr el proyecto es:

```bash
python3 -m app
```

No uses `python app/main.py`; el entrypoint soportado es el módulo `app`.

## Uso básico

- Configura al menos un board en `GREENHOUSE_COMPANY_BOARDS`.
- Las vacantes nuevas se guardan en SQLite.
- Solo las vacantes nuevas y relevantes se notifican por Discord.
- La deduplicación se hace contra el batch actual y contra la base de datos.
