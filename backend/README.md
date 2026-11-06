API y motor de cálculo en Python.

## Autenticación

Configurá estas variables en el archivo `.env` de la raíz (consultá `.env.example`):

- `JWT_SECRET_KEY`: al menos 32 caracteres aleatorios; generala con `openssl rand -hex 32`.
- `AUTH_ALLOWED_ORIGINS`: arreglo JSON de orígenes de confianza del frontend, por ejemplo, `["http://localhost:5173"]`.
- `AUTH_COOKIE_SECURE`: `false` solo para HTTP local; usá `true` con HTTPS en producción.
- `ACCESS_TOKEN_MINUTES`: el valor predeterminado es 15.
- `REFRESH_TOKEN_DAYS`: el valor predeterminado es 7. La rotación conserva la fecha de vencimiento original de la sesión.

Ejecutá `uv sync` y luego `uv run alembic upgrade head`, con las variables de entorno
de la base de datos configuradas, antes de iniciar la API. Con Docker, ejecutá
`docker compose exec backend alembic upgrade head` después de reconstruir el backend.

`POST /auth/login` acepta los campos de formulario OAuth2 `username` (correo electrónico) y `password`.
`POST /auth/register` acepta un JSON con `name`, `email` y `password`.
Ambos devuelven un JWT de acceso y establecen una cookie de renovación HttpOnly.
Las solicitudes POST del navegador a los endpoints de autenticación deben incluir
un encabezado Origin de la lista de orígenes permitidos (esto también se aplica a
los clientes de API y a la función Try it out de Swagger; agregá explícitamente
el origen de la documentación si es necesario).
`POST /auth/refresh` rota esa cookie y devuelve un nuevo JWT de acceso.
`POST /auth/logout` revoca toda la familia actual de tokens de renovación y elimina la cookie.
`GET /auth/me` es un ejemplo de endpoint protegido que utiliza el JWT de acceso como token Bearer.
Cerrar sesión no invalida los JWT de acceso ya emitidos antes de su vencimiento.
Los tokens utilizados se conservan para detectar su reutilización; no los elimines
antes de que venza la familia. Cada inicio de sesión crea una familia independiente.

El cliente Vue restaura la sesión al iniciarse y proporciona `login`, `register`,
`logout` y `authenticatedFetch` en `src/api/auth.ts`. Usá `authenticatedFetch`
para las llamadas a la API protegidas (con rutas relativas como `/auth/me`). Reintenta
una vez tras recibir un código 401 y redirige a `/login` si falla la renovación.
Los JWT de acceso se mantienen en memoria.
La aplicación actual no tiene rutas de producto protegidas; agregar autenticación
no restringe sus páginas públicas de calculadoras. El formulario de cuenta está en `/login`.

La cookie predeterminada utiliza SameSite=Lax y admite despliegues en el mismo sitio,
incluido el proxy `/api` existente. Desplegar el frontend y la API en sitios distintos
requiere revisar SameSite=None, HTTPS y las restricciones de cookies de terceros.
Mantené las comprobaciones explícitas de Origin. Un proxy inverso nunca debe almacenar
en caché las respuestas que contienen tokens.
