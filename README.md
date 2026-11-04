# Calculadora ganadera

App de seguimiento del ciclo ganadero: cría, recría y engorde.

## Tecnologías

- **Frontend:** aplicación web progresiva (PWA) con Vue 3, Vite y TypeScript
- **Backend:** Python 3.14 con FastAPI, SQLAlchemy y Alembic
- **Base de datos:** PostgreSQL 16 con PostGIS 3

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | API y motor de cálculo |
| `frontend/` | Aplicación web progresiva |
| `docs/` | Diagramas, definiciones y material de referencia del clúster |

## Cómo levantar el proyecto

### Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/), solo para instalar el pre-commit
- [Node 24](https://nodejs.org/), solo si se trabaja en el frontend fuera de Docker (para que el editor, eslint y las pruebas anden en la compu)

### Primera vez

1. Copiar el archivo de variables de entorno. Los valores de ejemplo sirven para trabajar en local.

   ```
   cp .env.example .env
   ```

2. Levantar la base, el backend y el frontend:

   ```
   docker compose up -d
   ```

3. Crear las tablas y cargar los datos de referencia:

   ```
   docker compose run --rm backend alembic upgrade head
   ```

4. Activar el pre-commit, que corre ruff antes de cada commit:

   ```
   uvx pre-commit install
   ```

Con eso la app queda en http://localhost:5173 y la API en http://localhost:8000. La documentación interactiva está en http://localhost:8000/docs y el estado del servicio en http://localhost:8000/health.

### Uso diario

| Acción | Comando |
|---|---|
| Levantar todo | `docker compose up -d` |
| Ver los logs del backend | `docker compose logs -f backend` |
| Ver los logs del frontend | `docker compose logs -f frontend` |
| Aplicar migraciones nuevas | `docker compose run --rm backend alembic upgrade head` |
| Correr las pruebas del backend | `docker compose run --rm backend pytest` |
| Correr las pruebas del frontend | `docker compose run --rm frontend npm run test:unit -- --run` |
| Revisar el formato del backend | `docker compose run --rm backend ruff check .` |
| Revisar el frontend (eslint y prettier) | `docker compose run --rm frontend sh -c "npm run lint && npm run format:check"` |
| Apagar todo | `docker compose down` |

El backend y el frontend se recargan solos al guardar cambios en `backend/` o `frontend/`. Las pruebas usan una base aparte (`<base>_test`) que se crea sola, así que no tocan los datos de desarrollo.

### Si cambian las dependencias

Cuando alguien modifica `backend/pyproject.toml` o `frontend/package.json`, hay que reconstruir las imágenes:

```
docker compose up -d --build
```

### Empezar de cero con la base

Postgres lee el usuario, la clave y el nombre de la base del `.env` solo la primera vez que crea el volumen. Si se cambian esos valores, o si se quiere borrar todo, hay que eliminar el volumen y volver a migrar:

```
docker compose down -v
docker compose up -d
docker compose run --rm backend alembic upgrade head
```

> `down -v` borra todos los datos de la base local.

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
- El CI corre ruff y las pruebas del backend, y eslint, prettier, los tipos, las pruebas y el build del frontend en cada pull request. Tiene que pasar antes de integrarlo.
- Después de integrarlo, se borra la rama.

### Commits

Mensajes cortos, en presente y con el mismo prefijo que las ramas:

```
feat: agrega el cálculo de receptividad
fix: corrige el área de los polígonos
docs: actualiza el diagrama de componentes
chore: configura postgres
```

## Estado

En desarrollo. Están listos el backend base (base de datos, migraciones, datos de referencia y pruebas) y el frontend base (PWA instalable con la navegación entre secciones). Todavía no hay calculadoras.
