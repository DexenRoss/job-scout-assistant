Actúa como un ingeniero backend senior en Python. Quiero que trabajes SOBRE mi repo actual, con cambios mínimos pero sólidos. No rehagas el proyecto desde cero. No cambies la arquitectura base salvo donde sea necesario para corregir problemas reales.

Estoy en el Sprint 1.1 de saneamiento técnico de un proyecto llamado “job-scout-assistant”.

Objetivo:
corregir problemas reales del Sprint 1 sin mezclar todavía scoring avanzado, tailoring de CV, frontend, Docker ni nuevas fuentes.

Contexto del proyecto:
- Python
- SQLite
- Greenhouse como fuente inicial
- Discord webhook para notificaciones
- arquitectura por carpetas: app, core, sources, pipeline, notifications, storage

Problemas detectados que debes corregir:

1. Problema de ejecución
Actualmente el proyecto falla si se ejecuta como:
- python app/main.py

y solo funciona como:
- python -m app.main

Necesito que dejes una forma oficial, clara y consistente de ejecución.
Puedes resolverlo de una manera limpia, pero no quiero hacks feos ni manipulación rara de sys.path.
Quiero que:
- la estructura quede consistente
- el README explique la forma correcta de correrlo
- los imports sigan siendo limpios y mantenibles

2. Bug de duplicados dentro de la misma corrida
La deduplicación actual revisa contra la base de datos, pero no deduplica correctamente dentro del batch actual en memoria.
Eso puede causar que:
- una vacante repetida en la misma corrida se procese dos veces
- se cuente como insertada más de una vez
- incluso se notifique más de una vez

Necesito que corrijas esto.
Quiero deduplicación en dos capas:
- contra el batch actual
- contra storage

La clave de deduplicación debe usar:
- source + external_id
- y si external_id no existe o no es confiable, usar url como fallback

3. Bug de conteo e inserción
Actualmente el flujo parece contar como insertada una vacante aunque SQLite la ignore por duplicada.
Necesito que:
- insertar devuelva claramente si la inserción ocurrió o no
- solo se incremente inserted_count si realmente se insertó
- solo se agregue a notificación si realmente fue nueva e insertada
- los logs reflejen números reales

4. README incompleto / inconsistente
El README actual está roto o incompleto.
Quiero que lo reescribas de forma mínima pero correcta, incluyendo:
- qué hace el proyecto
- estructura breve
- instalación
- creación de entorno virtual
- instalación de dependencias
- cómo configurar .env
- cómo ejecutar el proyecto
- notas básicas de uso

Hazlo corto, claro y correcto.

5. Higiene del repo
Necesito mejorar `.gitignore`.
Debe ignorar como mínimo:
- .env
- entornos virtuales
- __pycache__/
- *.pyc
- archivos de base de datos locales si aplica
- caches comunes de Python/test

No borres archivos del repo automáticamente si no hace falta, pero sí deja `.gitignore` correcto.

6. Coherencia del Sprint 1
Revisa si `playwright` realmente se usa.
Si no se usa en este Sprint 1, no lo fuerces.
Puedes:
- quitarlo de requirements.txt si no aporta nada todavía
o
- dejarlo solo si el proyecto realmente lo usa ya
Quiero coherencia entre código, dependencias y README.

Restricciones:
- NO reescribas todo el proyecto
- NO cambies Greenhouse por otra fuente
- NO metas nuevas features
- NO metas ORM
- NO metas frontend
- NO metas Docker
- NO metas CV tailoring
- NO metas scheduler todavía
- NO improvises arquitectura nueva

Lo que sí quiero:
- cambios concretos
- diffs pequeños o moderados
- código limpio
- responsabilidades bien separadas
- mantener la arquitectura actual lo más posible

Revisión técnica esperada:
- revisa el flujo completo desde app/main.py
- revisa storage/repositories.py
- revisa pipeline/deduplicate_jobs.py
- revisa README.md
- revisa requirements.txt
- revisa .gitignore

Entregable:
1. Aplica los cambios directamente en el repo
2. Muéstrame un resumen claro de:
   - qué archivos cambiaste
   - qué problema resolvió cada cambio
3. Incluye cualquier comando exacto que deba correr para validar
4. No me des teoría larga; dame cambios concretos y justificados

Criterio de éxito:
- el proyecto tiene una forma oficial y clara de ejecución
- no se notifican duplicados dentro de la misma corrida
- inserted_count refleja inserciones reales
- README queda usable
- .gitignore queda correcto
- requirements.txt queda coherente con el código actual