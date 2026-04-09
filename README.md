# Job Scout Assistant

MVP del Sprint 1 para descubrir vacantes, normalizarlas, filtrarlas, deduplicarlas, guardarlas en SQLite y notificar vacantes relevantes por Discord.

## Arquitectura

El proyecto está dividido por responsabilidades:

- `core/`: configuración, logging y modelos internos
- `sources/`: conectores a fuentes externas
- `pipeline/`: descubrimiento, deduplicación y filtrado
- `storage/`: SQLite y repositorio
- `notifications/`: cliente y plantillas de Discord
- `app/`: orquestación principal

## Requisitos

- Python 3.11+
- Entorno virtual recomendado

## Instalación

```bash
python -m venv .venv
source JSA/bin/activate