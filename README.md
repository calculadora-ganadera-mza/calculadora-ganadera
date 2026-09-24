# Calculadora ganadera

App de seguimiento del ciclo ganadero: cría, recría y engorde.

## Tecnologías

- **Frontend:** aplicación web progresiva (PWA)
- **Backend:** Python
- **Base de datos:** PostgreSQL con PostGIS

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | API y motor de cálculo |
| `frontend/` | Aplicación web progresiva |
| `docs/` | Diagramas, definiciones y material de referencia del clúster |

## Forma de trabajo

### Ramas

- `main` es la única rama permanente y siempre tiene que funcionar.
- Nadie sube cambios directo a `main`. Todo entra por pull request.
- Cada tarea se trabaja en una rama propia que sale de `main` y dura pocos días.

Nombre de las ramas: `tipo/numero-de-issue-descripcion-corta`

| Tipo | Uso | Ejemplo |
|---|---|---|
| `feat` | Funcionalidad nueva | `feat/12-calculo-receptividad` |
| `fix` | Corrección de un error | `fix/18-error-en-poligonos` |
| `docs` | Documentación | `docs/5-diagrama-componentes` |
| `chore` | Configuración y mantenimiento | `chore/3-configurar-postgres` |

### Pull requests

- Todo pull request lo revisa y aprueba al menos otro integrante del equipo antes de integrarse.
- Cada pull request resuelve una sola tarea y referencia su issue.
- Después de integrarlo, se borra la rama.

### Commits

Mensajes cortos, en presente y con el mismo prefijo que las ramas:

## Estado

En etapa de análisis y diseño. Todavía no hay código.