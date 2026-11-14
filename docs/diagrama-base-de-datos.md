# Diagrama de la base de datos

Modelo de datos vigente, generado a partir de los modelos de `backend/app/models/`. Si se agrega o cambia una tabla, este diagrama se actualiza en el mismo pull request.

```mermaid
erDiagram
    app_user ||--o{ refresh_session : "abre"
    app_user ||--o{ scenario : "registra"
    scenario ||--o{ season : "tiene"
    scenario ||--o{ production_unit : "se divide en"
    production_unit ||--o{ water_point : "contiene"
    season ||--o{ herd_season : "agrupa"
    production_unit ||--o{ herd_season : "tiene uno por campaña"
    herd_season ||--o{ herd_category : "se compone de"
    animal_category ||--o{ herd_category : "clasifica"

    app_user {
        int id PK
        string name
        string email UK
        string password_hash
        role role "producer, technician o admin; por defecto producer"
        bool email_verified "por defecto false"
        bool is_active "por defecto true"
        timestamptz created_at
    }

    refresh_session {
        int id PK
        int user_id FK "se borra con el usuario"
        string token_hash UK
        string family_id "agrupa los tokens de una misma sesión"
        timestamptz expires_at
        bool revoked
        timestamptz created_at
    }

    scenario {
        int id PK
        int user_id FK "se borra con el usuario"
        string name
        bool is_main "uno solo por usuario"
        geometry_point location "SRID 4326, opcional"
        timestamptz created_at
    }

    season {
        int id PK
        int scenario_id FK "se borra con el establecimiento"
        date start_date
        date end_date "posterior a start_date"
        float rainfall_mm "lluvia de la campaña anterior, mayor o igual a 0, opcional"
        timestamptz created_at
        timestamptz updated_at
    }

    production_unit {
        int id PK
        int scenario_id FK "se borra con el establecimiento"
        string name
        production_system production_system "rainfed, irrigated o feedlot"
        geometry_polygon polygon "SRID 4326, polígono válido"
        float area_ha "calculada por PostGIS sobre geography"
        timestamptz created_at
    }

    water_point {
        int id PK
        int production_unit_id FK "se borra con el sector"
        string name
        geometry_point location "SRID 4326, dentro del sector"
        float refill_l_day "mayor que 0, opcional"
        timestamptz created_at
    }

    herd_season {
        int id PK
        int scenario_id FK "parte de las dos claves compuestas"
        int season_id FK "con scenario_id, apunta a season"
        int production_unit_id FK "con scenario_id, apunta a production_unit"
        date breeding_start "opcional, junto con breeding_end"
        date breeding_end "posterior a breeding_start"
        range_condition range_condition "fair, good o very_good"
        float replacement_rate "entre 0 y 1, opcional"
        float weaning_rate "entre 0 y 1, opcional"
        bool early_weaning "por defecto false"
        bool supplemented "por defecto false"
        float calving_body_condition "entre 1 y 5, opcional"
        timestamptz updated_at
    }

    herd_category {
        int id PK
        int herd_season_id FK "se borra con el rodeo de la campaña"
        int animal_category_id FK
        int quantity "mayor o igual a 0"
    }

    animal_category {
        int id PK
        string code UK "cow, bull, heifer, calf o steer"
        string name UK
        float cow_equivalent "mayor que 0"
        float summer_water_l_day "mayor que 0"
        float winter_water_l_day "mayor que 0"
    }

    parameter {
        int id PK
        string key UK
        string description
        float value
        string unit
        bool confirmed "por defecto false"
        bool producer_editable "por defecto false"
    }
```

## Reglas que el diagrama no muestra

- **Un establecimiento principal por usuario:** índice único parcial `uq_scenario_main_per_user` sobre `user_id` cuando `is_main` es verdadero.
- **Campañas sin superposición:** dentro de un mismo establecimiento, dos campañas no pueden compartir días (`ex_season_no_overlap`, restricción de exclusión con GiST).
- **Rodeo de la campaña dentro del mismo establecimiento:** `herd_season` apunta a `season` y a `production_unit` con claves compuestas que incluyen `scenario_id`. Así la campaña y el sector siempre son del mismo establecimiento. Hay un solo rodeo por campaña y sector.
- **Una cantidad por categoría:** `herd_category` no repite la misma categoría dentro de un rodeo.
- **Superficie:** `area_ha` es una columna calculada y guardada (`ST_Area(polygon::geography) / 10000`). No se escribe a mano.
- **Borrado en cascada:** al borrar un usuario se borra todo lo suyo. Lo mismo pasa con un establecimiento, un sector, una campaña o un rodeo: arrastran lo que depende de ellos. Una categoría animal en uso no se puede borrar.
- **Tablas sueltas:** `parameter` no se relaciona con otras tablas. La consulta el motor de cálculo por su `key`.
