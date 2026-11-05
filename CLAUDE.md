# Calculadora ganadera

Aplicación web progresiva (PWA) para el seguimiento del ciclo ganadero bovino (cría, recría y engorde), impulsada por el Clúster Ganadero de Mendoza. Tiene cuatro calculadoras independientes, una sección de campo con mapa, seguimiento campaña a campaña y avisos al celular.

## Documentación de referencia

Antes de diseñar o programar algo del dominio, leer:

- `docs/definiciones-del-proyecto.md`: decisiones vigentes. Si otro documento lo contradice, vale este.
- `docs/como-funciona-cada-calculadora.md`: datos, pasos de cálculo y resultados de cada calculadora.
- `docs/diagrama-base-de-datos.pdf`: modelo de datos completo.

Si algo no está definido en esos documentos, no inventarlo: preguntar.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python 3.14 + FastAPI |
| Validación | Pydantic v2 y pydantic-settings |
| Base de datos | PostgreSQL 16 + PostGIS 3 |
| Acceso a datos | SQLAlchemy 2 (estilo 2.0, tipado) + GeoAlchemy2 |
| Migraciones | Alembic |
| Sesión | JWT, con token de acceso corto y token de renovación |
| Frontend | Vue 3 + Vite + TypeScript, con vite-plugin-pwa |
| Estado del frontend | Pinia |
| Mapas | Leaflet + Geoman |
| Avisos | Web Push (pywebpush) y una tarea diaria programada |
| Pruebas | pytest en el backend y Vitest en el frontend |
| Formato | ruff en el backend; eslint y prettier en el frontend |
| Dependencias del backend | uv, con `pyproject.toml` |

## Principios de arquitectura

- Todo el cálculo ocurre en el backend. El frontend no calcula nada.
- El motor de cálculo (`backend/app/calculators/`) son funciones puras: reciben datos y parámetros, devuelven resultados. No acceden a la base ni dependen de FastAPI. Se prueban con casos resueltos a mano.
- Ningún valor de referencia va escrito en el código: todo sale de la tabla `parametro` o de las tablas de referencia, porque el administrador los cambia sin tocar el código.
- Cada cálculo guardado registra los parámetros con los que se hizo.
- Superficies y distancias se calculan con PostGIS sobre `geography`, no en Python.

## Principios de programación

Todo el código y sus revisiones siguen estos principios:

- **KISS:** la solución más simple que funcione.
- **DRY:** cada dato o regla vive en un solo lugar.
- **YAGNI:** no construir algo hasta que haga falta.
- **SOLID:** responsabilidad única, abierto/cerrado, sustitución de Liskov, segregación de interfaces e inversión de dependencias.
- **Separación de responsabilidades:** cada parte se ocupa de una sola cosa.
- **Bajo acoplamiento y alta cohesión:** las partes dependen poco entre sí, y lo que está junto tiene relación.
- **Composición antes que herencia:** combinar piezas en vez de armar jerarquías de clases.
- **Fallar rápido:** un error se detecta lo antes posible, sin seguir con datos inválidos.
- **Menor sorpresa:** el código hace lo que su nombre sugiere.
- **12-factor:** la app se configura desde el entorno y se despliega igual en todos lados ([12factor.net](https://12factor.net)).
- **Mínimo privilegio:** cada usuario y cada servicio accede solo a lo que necesita.

Si dos principios chocan, KISS y YAGNI le ganan a DRY: algo se unifica recién cuando se repite por tercera vez.

## Estructura del repositorio

```
backend/
  app/
    main.py
    api/            rutas
    models/         tablas (SQLAlchemy)
    schemas/        entrada y salida (Pydantic)
    calculators/    motor de cálculo, funciones puras
    core/           configuración, seguridad, conexión
  alembic/
  tests/
  pyproject.toml
  Dockerfile
frontend/
  src/
    views/          una pantalla por sección
    components/     piezas reutilizables
    router/         rutas
    stores/         estado compartido (Pinia)
    api/            pedidos al backend
  public/           íconos de la PWA
docs/
docker-compose.yml
.env.example
```

## Convenciones

- **Idioma:** todo el código va en inglés: nombres de tablas, columnas, tipos enumerados y sus valores, variables, funciones, clases, archivos, rutas de la API y claves del JSON. En español van los comentarios, los docstrings y todo texto que lee una persona: mensajes de error, textos en pantalla, logs, descripciones de parámetros.
- **Nombres:** en minúsculas y con guiones bajos en Python y en la base (`production_unit`, `herd_category`). Los términos del dominio se traducen siempre igual, según el glosario.
- **Ramas:** `tipo/numero-de-issue-descripcion-corta`, con tipo `feat`, `fix`, `docs` o `chore`. Nadie sube directo a `main`; todo entra por pull request, con la plantilla de `.github/pull_request_template.md`.
- **Commits:** cortos, en presente y con el mismo prefijo que la rama (`feat: ...`, `chore: ...`).
- **Una tarea por pull request.**
- **Pruebas:** toda lógica nueva lleva pruebas. Las del motor de cálculo usan casos con resultado conocido.
- **Formato:** el código pasa ruff sin errores antes de cada commit.

## Glosario

Traducción fija de los términos del dominio. El código usa la columna de la derecha.

| Español | Inglés |
|---|---|
| usuario | `app_user` (clase `User`; `user` es palabra reservada en Postgres) |
| rol: productor / técnico / administrador | `role`: `producer` / `technician` / `admin` |
| categoría animal | `animal_category` |
| EV (equivalente vaca) | `cow_equivalent` |
| consumo de materia seca (MS) | `dm_intake_kg_year` |
| agua en verano / invierno | `summer_water_l_day` / `winter_water_l_day` |
| parámetro (clave, valor, unidad) | `parameter` (`key`, `value`, `unit`) |
| escenario | `scenario` |
| unidad productiva | `production_unit` |
| ambiente: secano / bajo riego / corral | `production_system`: `rainfed` / `irrigated` / `feedlot` |
| superficie | `area_ha` |
| aguada | `water_point` |
| litros que repone por día | `refill_l_day` |
| campaña | `season` |
| rodeo de la campaña | `herd_season` |
| cantidad por categoría | `herd_category` |
| entore (inicio / fin) | `breeding_start` / `breeding_end` |
| estado del campo: regular / bueno / muy bueno | `range_condition`: `fair` / `good` / `very_good` |
| % reposición / % destete | `replacement_rate` / `weaning_rate` |
| condición corporal al parto | `calving_body_condition` |
| precipitación | `rainfall_mm` |
| receptividad | `carrying_capacity` |

## Comandos

- Levantar todo: `docker compose up`
- Migraciones: `docker compose run --rm backend alembic upgrade head`
- Pruebas: `docker compose run --rm backend pytest`
- Formato: `ruff check . && ruff format .` dentro de `backend/`
- Pruebas del frontend: `npm run test:unit` dentro de `frontend/`
- Lint y formato del frontend: `npm run lint` y `npm run format` dentro de `frontend/`
- Tipos del frontend: `npm run type-check` dentro de `frontend/`

(Actualizar esta sección si los comandos cambian.)
