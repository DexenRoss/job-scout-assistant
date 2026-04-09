Actúa como un ingeniero backend senior en Python, con criterio fuerte de arquitectura, modularidad y mantenibilidad.

Estoy construyendo un proyecto personal llamado provisionalmente “Job Scout Assistant”.

Quiero construir un asistente que monitoree vacantes relevantes para mi perfil, las filtre, guarde las nuevas y me notifique por Discord con el link de la vacante.

IMPORTANTE:
Este sistema NO debe aplicar automáticamente a vacantes.
NO debe hacer auto-submit de formularios.
NO debe simular comportamiento de auto-apply.
Su función en esta fase es solo:
- descubrir vacantes,
- normalizarlas,
- filtrarlas,
- deduplicarlas,
- guardarlas,
- y notificarme.

Quiero que trabajes con arquitectura limpia y modular.
No improvises.
No mezcles scraping con lógica de negocio.
No mezcles storage con notifications.
No me des una solución monolítica en un solo archivo.
Quiero archivos separados, rutas exactas y código listo para crecer.

## Objetivo del Sprint 1

Entregar un MVP funcional que:

1. consulte al menos una fuente real de vacantes;
2. extraiga vacantes;
3. convierta los resultados a un modelo interno unificado;
4. elimine duplicados;
5. aplique filtros básicos por texto;
6. guarde las vacantes en SQLite;
7. mande alertas por Discord webhook;
8. permita ejecución manual desde un entrypoint;
9. deje lista la base para luego agregar scheduler y scoring.

## Stack requerido

- Python 3.11+
- Playwright
- Pydantic
- SQLite
- requests o httpx para Discord webhook
- dotenv para variables de entorno
- logging estándar de Python

## Restricciones técnicas

- Debe haber separación clara entre:
  - configuración
  - modelos
  - fuentes
  - pipeline
  - almacenamiento
  - notificaciones
  - app/orquestación
- Usa tipado
- Usa clases o funciones bien separadas
- No uses dicts caóticos como contrato principal entre módulos
- El modelo interno debe ser estable aunque en el futuro cambien las fuentes
- El código debe ser legible y extensible
- No metas frontend
- No metas IA todavía
- No metas tailoring de CV todavía
- No metas Docker todavía, salvo que sea estrictamente necesario
- No metas dependencias innecesarias

## Arquitectura obligatoria del proyecto

Quiero que uses esta estructura base y me entregues los archivos completos con su contenido:

job-scout-assistant/
│
├── app/
│   └── main.py
│
├── core/
│   ├── config.py
│   ├── logger.py
│   └── models.py
│
├── sources/
│   ├── base.py
│   └── greenhouse.py
│
├── pipeline/
│   ├── deduplicate_jobs.py
│   ├── filter_jobs.py
│   └── discover_jobs.py
│
├── notifications/
│   ├── discord.py
│   └── templates.py
│
├── storage/
│   ├── db.py
│   └── repositories.py
│
├── data/
│   └── .gitkeep
│
├── .env.example
├── requirements.txt
└── README.md

## Decisión de fuente inicial

Para este Sprint 1, usa una sola fuente inicial:
- Greenhouse

Quiero que diseñes la integración de forma que más adelante se pueda agregar Lever sin romper la arquitectura.

## Modelo interno obligatorio

Define un modelo Pydantic llamado `JobPosting` con al menos estos campos:

- source: str
- external_id: str
- title: str
- company: str
- location: str | None
- employment_type: str | None
- seniority: str | None
- salary_text: str | None
- url: str
- description: str | None
- date_posted: str | None
- discovered_at: datetime
- normalized_tags: list[str]
- is_relevant: bool = False
- relevance_reason: str | None = None
- status: str = "new"

Si consideras necesario agregar uno o dos campos más para robustez, hazlo, pero sin complicar de más.

## Reglas de persistencia

Usa SQLite.

Necesito una tabla para vacantes descubiertas con una restricción de unicidad basada en:
- source + external_id
o, si no existe external_id confiable, entonces por url

Quiero una capa de repositorio simple que permita:
- inicializar base de datos
- insertar vacante si no existe
- revisar si una vacante ya existe
- marcar vacante como notificada
- listar vacantes nuevas si hace falta

No metas un ORM completo para este sprint.
Usa sqlite3 estándar, salvo que tengas una razón muy fuerte y clara para otra cosa.

## Reglas de filtrado v1

Implementa filtros básicos basados en texto.

Debe haber configuración para:
- include_keywords
- exclude_keywords

Haz el matching sobre:
- title
- description
- company
- normalized_tags

Reglas:
- si contiene alguna palabra excluida, descártala
- si contiene al menos una palabra incluida, puede pasar
- si no contiene ninguna incluida, descártala

También quiero que el filtro pueda dejar una breve razón en `relevance_reason`.

## Reglas de deduplicación

Crea un módulo específico para deduplicación.

Regla:
- una vacante se considera duplicada si ya existe en storage por source + external_id
- si external_id no está disponible, usar url como fallback

No mezcles esta lógica en el scraper.

## Reglas para la fuente Greenhouse

Quiero una implementación inicial limpia.
Si Greenhouse ofrece una forma más estructurada o estable de consultar puestos, prefiero eso sobre scraping frágil del HTML.

Tu objetivo es:
- obtener vacantes
- mapearlas a `JobPosting`
- no sobrecomplicar el extractor

No quiero que inventes compatibilidad con todas las empresas de Greenhouse si eso hace el código frágil.
Quiero una primera versión razonable y mantenible.

## Notificación por Discord

Implementa notificación vía webhook.

Quiero un mensaje simple pero útil, incluyendo:
- título
- empresa
- ubicación
- fuente
- razón de relevancia
- link

Separa:
- cliente de Discord
- template/formateo del mensaje

No pongas la plantilla incrustada en cualquier parte del pipeline.

## Configuración

Crea configuración centralizada desde `.env`.

Debe soportar como mínimo:
- DISCORD_WEBHOOK_URL
- DATABASE_PATH
- INCLUDE_KEYWORDS
- EXCLUDE_KEYWORDS
- GREENHOUSE_ENABLED

Si hace falta, puedes agregar:
- GREENHOUSE_COMPANY_BOARDS
o equivalente, pero explícame bien su formato.

## Logging

Agrega logging básico útil.
Quiero logs para:
- inicio de ejecución
- número de vacantes encontradas
- número de vacantes nuevas
- número de vacantes filtradas como relevantes
- número de notificaciones enviadas
- errores importantes

No llenes el código de prints.

## Entry point

Crea `app/main.py` como orquestador.

Flujo esperado:
1. cargar config
2. inicializar logger
3. inicializar db
4. consultar fuente(s)
5. normalizar / construir `JobPosting`
6. deduplicar
7. filtrar
8. persistir
9. notificar relevantes
10. marcar notificadas
11. terminar con logs claros

## Entregable esperado

Quiero que me entregues:

1. Todos los archivos completos, con rutas exactas
2. El contenido exacto de cada archivo
3. Dependencias en `requirements.txt`
4. `.env.example`
5. Instrucciones mínimas de ejecución en `README.md`

## Formato de respuesta obligatorio

Responde en este orden exacto:

1. Breve explicación de la arquitectura elegida
2. Árbol del proyecto
3. Archivos completos uno por uno, con su ruta exacta antes del contenido
4. Instrucciones de instalación y ejecución
5. Posibles mejoras para Sprint 2, pero separadas claramente y sin mezclarlas en el código del Sprint 1

## Importante

No me des pseudocódigo.
No me des fragmentos incompletos.
No me digas “aquí podrías agregar”.
Quiero una primera versión funcional completa.
Si tienes que simplificar algo para mantenerlo sólido, simplifícalo.
Prefiero una base limpia y ejecutable a una solución ambiciosa pero rota.