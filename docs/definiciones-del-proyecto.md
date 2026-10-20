# Definiciones del proyecto

Calculadora ganadera · actualizado al 20 de octubre de 2026

Este documento reúne las decisiones vigentes del proyecto. Es la referencia del equipo: si otro documento lo contradice, vale este.

Cada punto está definido, salvo que lleve una de estas marcas:

- **Sugerencia del equipo:** está incorporado al diseño, pero falta que el clúster lo confirme.
- **Pendiente:** falta definirlo.

El funcionamiento de cada calculadora está explicado en `como-funciona-cada-calculadora`. Acá solo figuran las decisiones.

---

## 1. Alcance

- **Producto:** aplicación web progresiva (PWA) para el Clúster Ganadero de Mendoza, con cuatro calculadoras para el ciclo ganadero: cría, recría y engorde.
- **Zona:** provincia de Mendoza. Por ahora, solo la llanura (Lavalle, San Martín, Santa Rosa, La Paz, San Rafael y General Alvear), que es la zona con datos de receptividad publicados. Malargüe y el oeste se suman cuando haya datos.
- **Especie:** solo ganado bovino. No se contemplan otras especies que compartan el campo.
- **Dispositivos:** computadora y Android como prioridad. iPhone también se contempla.
- **Alojamiento:** la aplicación quedaría alojada en el sitio del clúster.
- **Entrega:** un producto mínimo viable en diciembre de 2026.
- **Alcance del producto mínimo viable:** Pendiente. Falta definir qué entra en diciembre y qué queda para después.

## 2. Usuarios

- **Registro:** abierto. Cualquier persona puede crear una cuenta, con verificación del correo.
- **Rol:** cada usuario tiene un solo rol: productor, técnico o administrador.
- **Productor y técnico:** por ahora ven y hacen lo mismo.
- **Administrador:** además, carga y corrige las tablas de referencia y los parámetros.

## 3. Organización de los datos

Los datos no pertenecen a ninguna calculadora. Viven en cuatro niveles, y las calculadoras los leen de ahí.

| Nivel | Qué es | Qué guarda |
|---|---|---|
| Escenario | El establecimiento. | Nombre, zona y ubicación. |
| Unidad productiva | Un sector del campo que se usa para cría, recría o engorde. | Ambiente, polígono, superficie y aguadas. |
| Campaña | Un ciclo anual del establecimiento. | Fecha de inicio y de fin, y precipitación registrada (opcional). |
| Rodeo de la campaña | Los animales de una unidad en una campaña. | Cantidad por categoría, período de entore, estado del campo, porcentajes de reposición y de destete, y condición corporal al parto. |

- **Zona:** una de las seis subzonas de la llanura, que se elige de una lista. Cada subzona tiene su lluvia media y su lluvia confiable.
- **Categorías del rodeo:** el productor carga la cantidad de cada categoría de animal que tenga la unidad: vacas, toros, vaquillonas, terneros, novillitos u otras. Las categorías salen de una tabla que mantiene el administrador. No hace falta indicar para qué se usa la unidad.
- **Rodeo por unidad:** el productor puede repartir su hacienda entre varias unidades. Cada cálculo se hace sobre el rodeo de esa unidad, no sobre el total del establecimiento.
- **Subdivisión interna:** si una unidad se divide en lotes y el rodeo rota entre ellos, se carga como una sola unidad. La rotación es manejo del productor y no cambia los cálculos.
- **Precipitación de la campaña:** es opcional y queda como historial. Los cálculos usan la lluvia confiable de la subzona.
- **Histórico:** un escenario acumula campañas. Las campañas anteriores no se modifican.
- **Meses de la campaña:** Pendiente.

## 4. Campo y aguadas

- **Campo:** el productor dibuja el polígono de cada unidad sobre un mapa.
- **Aguadas:** se marcan como puntos sobre el mismo mapa.
- **Alcance de una aguada:** 2,5 km. Es un parámetro y se puede cambiar.
- **Superficie aprovechable:** la parte del polígono que queda dentro del alcance de alguna aguada. Si los alcances se superponen, la superficie se cuenta una sola vez.
- **Agua que repone la aguada:** litros por día, dato opcional. Se pide lo que repone, no lo que almacena.
- **Estado de la aguada:** no se modela. Toda aguada marcada se considera operativa.

## 5. Ambientes

Cada unidad productiva tiene uno de tres ambientes.

- **Secano:** solo recibe agua de lluvia.
- **Bajo riego:** recibe riego adicional, con agua subterránea o con derecho de riego superficial. La lluvia no interviene en el cálculo, porque el riego se hace igual por salinidad, frecuencia y disponibilidad. Qué se calcula en este ambiente está pendiente: las pasturas que mencionó el clúster incluyen cultivos para silaje y heno, que se cortan y se conservan, además de los que se pastorean.
- **Corral:** la Receptividad y la Proyección no aplican, porque no hay pasto que calcular.

## 6. Calculadoras

Son cuatro, independientes entre sí, y se pueden usar en cualquier orden. Ninguna alimenta a otra. Todo el cálculo ocurre en el servidor.

### Receptividad ganadera y tamaño del rodeo

- **Unidad de trabajo:** todo se expresa en equivalentes vaca (EV).
- **Receptividad:** se calcula con el método de Guevara y otros (IADIZA, 1995), a partir de la lluvia confiable de la subzona. Después se corrige por estado del campo y por tecnologías de manejo.
- **Otra lluvia:** si el año viene distinto, el productor puede simular con otra precipitación sin modificar sus datos.
- **Límite por pasto:** superficie aprovechable dividida por la receptividad.
- **Límite por agua:** se calcula cuánta agua necesita el rodeo del límite por pasto, categoría por categoría. Si las aguadas cubren un porcentaje de esa necesidad, el límite por agua es ese mismo porcentaje del límite por pasto.
- **Rodeo máximo:** el menor entre el límite por pasto y el límite por agua. Se informa desglosado por categoría.
- **Sin dato de agua:** si no se cargó cuánto reponen las aguadas, se usa solo el límite por pasto y se aclara que el agua no se evaluó.
- **Termómetro de carga:** compara el rodeo actual, en EV, con el rodeo máximo. Va en esta calculadora.
- **Índices por estado del campo y por tecnología de manejo:** Pendiente.

### Proyección del estado del rodeo

- **Dónde aplica:** en unidades que tienen vacas.
- **Qué compara:** la oferta y la demanda de pasto, período por período a lo largo del año.
- **Períodos:** de resolución variable. Cercana a mensual en la época de mayor actividad, que arranca en octubre o noviembre, y cercana a trimestral desde mayo o junio.
- **Entore:** se carga como un período, con inicio y fin. No se contempla el servicio continuo, para promover el servicio estacionado.
- **Demanda:** depende del estado de las vacas en cada período, del porcentaje de destete del año anterior y del extra para llegar a la condición corporal buscada al entore. Las demás categorías de la unidad se suman con su consumo propio.
- **Resultado:** semáforo, período crítico y kilos de pasto faltantes.
- **Umbrales del semáforo:** Pendiente.
- **Consumo de vaquillonas de primera y segunda parición:** Pendiente.

### Conveniencia económica del destete

- **Qué evalúa:** el resultado de alimentar al ternero desde el destete hasta la venta.
- **Alimento:** si el productor conoce la cantidad, la carga. Si no, la calculadora la estima.
- **Método de estimación del alimento:** Pendiente.
- **Precio del ternero:** el precio por kilo cambia con el peso. Falta definir si se carga un solo precio o dos, uno al destete y otro a la venta. Pendiente.
- **Transporte:** no se incluye.

### Conveniencia de ganadería en corral

- **Qué evalúa:** el resultado de un ciclo de engorde a corral.
- **Modalidades:** corral propio y hotelería.
- **Cálculo base:** el de la planilla del clúster. El consumo diario es un porcentaje del peso vivo promedio, los días de estadía salen de los kilos a ganar divididos por la ganancia diaria, y el porcentaje de grano reparte el consumo entre maíz y forraje.
- **Precio del forraje:** opcional. Si no se carga, el resultado aclara que no lo incluye.
- **Etapas de la dieta:** como mínimo tres (adaptación, recría y terminación). Qué se carga en cada una está pendiente.
- **Forma de cobro de la hotelería:** Pendiente.

## 7. Valores de referencia

Todos son parámetros: el administrador los puede cambiar sin tocar el código.

| Valor | Dato | Origen |
|---|---|---|
| Consumo de un EV | 3.285 kg de materia seca por año (9 kg por día) | Planilla del clúster |
| Alcance de una aguada | 2,5 km | Clúster |
| Eficiencia de uso de la lluvia | 2,15 kg MS por ha por mm en herbáceas y 1,4 en leñosas | Guevara y otros (1995) |
| Forraje accesible | 80% de las herbáceas y 50% de las leñosas | Guevara y otros (1995) |
| Factor de uso del forraje | 30% | Guevara y otros (1995) y clúster |
| Lluvia media y confiable | Por subzona de la llanura (A a F) | Guevara y otros (1995) |
| Consumo de agua de un animal adulto | 70 litros por día en verano y 35 a 40 en invierno | Clúster |
| Consumo de agua por categoría | Tabla por categoría, en verano y en invierno | Clúster |
| Toros por vaca | 4 a 5 cada 100 vacas, hasta 6 o 7 en el noreste | Clúster |
| Consumo diario en corral | 3,5% del peso vivo | Clúster |

El equivalente vaca incluye el consumo del ternero hasta los 6 meses.

## 8. Costos y margen

- **Margen bruto:** incluye solo costos variables. No incluye amortizaciones ni costos financieros.
- **Alimento:** se incluye siempre.
- **Otros costos variables:** son opcionales en las dos calculadoras económicas.
- **Forma de carga:** desglosados por rubro, con un valor por cabeza para cada uno.
- **Rubros:** salen de un listado propio de cada calculadora, que se puede ampliar, con un rubro "Otros". Qué rubros tiene cada listado está pendiente.

## 9. Guardado de cálculos

- **Dos formas de guardar:** como resultado de la campaña o como simulación. Vale para las cuatro calculadoras.
- **Punto de partida:** cada calculadora arranca con los valores de la campaña. El productor los puede cambiar para simular sin modificar sus datos.
- **Guardar y actualizar la campaña:** si el cálculo usa valores distintos de los de la campaña, el productor puede elegir que la campaña se actualice con ellos.
- **Un resultado por campaña:** en Receptividad, Proyección y Destete. Si se guarda uno nuevo, el anterior pasa a ser una simulación.
- **Varios resultados por campaña:** en Corral, uno por ciclo. El seguimiento muestra el promedio y permite ver cada uno.
- **Borrar:** un cálculo guardado se puede borrar.
- **Deshacer:** la actualización de la campaña se puede deshacer solo si los datos no cambiaron después.
- **Parámetros usados:** cada cálculo guarda los valores de referencia con los que se hizo, para que un cambio posterior en las tablas no altere los resultados ya guardados.

## 10. Seguimiento

- **Evolución:** gráficos campaña a campaña de cada unidad productiva.
- **Comparación:** las unidades de un mismo escenario, una al lado de la otra.
- **Kilos de carne producidos por vaca:** Pendiente.

## 11. Avisos

- **Qué son:** notificaciones que llegan al dispositivo aunque la aplicación esté cerrada.
- **Anticipación:** cuatro avisos por evento, a 30, 15, 7 y 1 día.
- **Control:** el usuario los activa y desactiva por tipo de evento.
- **Eventos:** inicio del entore y retiro de los toros.
- **Vacunación:** con un calendario sanitario cargado por el administrador. Sugerencia del equipo. Por ahora el clúster informó la campaña anual de aftosa y brucelosis, de marzo a abril.
- **iPhone:** los avisos solo funcionan si el usuario instaló la aplicación en la pantalla de inicio. La aplicación lo explica en una pantalla.

## 12. Pantallas

La aplicación tiene cinco secciones.

| Sección | Para qué sirve |
|---|---|
| Inicio | Resumen de la campaña actual de cada unidad y próximos eventos. |
| Mi campo | Escenario, unidades, mapa, aguadas y datos de la campaña. |
| Calculadoras | Las cuatro calculadoras, cada una con su historial. |
| Seguimiento | Evolución campaña a campaña y comparación entre unidades. |
| Administración | Tablas de referencia y parámetros. Solo para administradores. |

En el celular la navegación va en una barra inferior. En la computadora, en un menú lateral.

## 13. Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| Validación | Pydantic |
| Base de datos | PostgreSQL + PostGIS |
| Acceso a datos | SQLAlchemy 2 + GeoAlchemy2 |
| Migraciones | Alembic |
| Sesión | JWT, con token de acceso corto y token de renovación |
| Frontend | Vue + Vite + TypeScript, con vite-plugin-pwa |
| Estado del frontend | Pinia |
| Mapas | Leaflet + Geoman |
| Avisos | Web Push (pywebpush) y una tarea diaria programada |
| Pruebas | pytest en el backend y Vitest en el frontend |
| Formato del código | ruff en el backend, eslint y prettier en el frontend |

- **Sin conexión:** por ahora no se calcula sin conexión.
- **Panel de administración:** pantallas propias dentro de la aplicación.
- **Nombres en el código:** por ahora en español. Se pasan al inglés más adelante.
- **Despliegue:** el desarrollo es local y el despliegue se hace al final.

## 14. Forma de trabajo

- **Equipo:** tres desarrolladores y un scrum master.
- **Repositorio:** uno solo, con `backend/`, `frontend/` y `docs/`.
- **Ramas y pull requests:** según el `README.md` del repositorio.
- **Código:** se escribe con Claude Code, a partir de un documento de contexto con estas definiciones.

## 15. Para más adelante

- **Malargüe y el oeste:** se suman cuando haya datos de receptividad.
- **Selección de la subzona en un mapa:** con un clic sobre la división, en lugar de la lista.
- **Lluvia mensual:** que el productor cargue cada mes y la aplicación sume el total de la campaña.
- **Vista del establecimiento completo:** el rodeo máximo total de todas las unidades frente al rodeo total.
- **Bajo riego y dieta por etapas:** se suman al modelo de datos cuando estén definidos.

## 16. Fuera de esta etapa

- Otras especies además de bovinos.
- Servicio continuo, con toro todo el año.
- Cálculo sin conexión.
- Estado o caudal parcial de las aguadas, y aguadas que solo tienen agua en algunos meses.
- Aguadas dibujadas como áreas en lugar de puntos.
- Registro de sombra y de comederos en el mapa.
- División del campo por imágenes satelitales.
- Una quinta calculadora para producción de alimento en finca.
- Cálculo de un destete potencial para compararlo con el real.
- Cruce de variables entre campañas para sacar conclusiones.
