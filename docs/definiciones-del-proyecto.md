# Definiciones del proyecto

Calculadora ganadera · actualizado al 14 de noviembre de 2026

Este documento reúne las decisiones vigentes del proyecto. Es la referencia del equipo: si otro documento lo contradice, vale este.

Cada punto está definido, salvo que lleve una de estas marcas:

- **Sugerencia del equipo:** está incorporado al diseño, pero falta que el clúster lo confirme.
- **Pendiente:** falta definirlo.

El funcionamiento de cada calculadora está explicado en `como-funciona-cada-calculadora`. Acá solo figuran las decisiones.

---

## 1. Alcance

- **Producto:** aplicación web progresiva (PWA) para el Clúster Ganadero de Mendoza, con cuatro calculadoras para el ciclo ganadero: cría, recría y engorde.
- **Zona:** provincia de Mendoza. El productor carga la lluvia de su campo, así que la calculadora no depende de la zona. Los coeficientes de Guevara y otros (1995) se midieron en la llanura; falta que el clúster confirme si acepta resultados fuera de ella.
- **Especie:** solo ganado bovino. No se contemplan otras especies que compartan el campo.
- **Dispositivos:** computadora y Android como prioridad. iPhone también se contempla.
- **Alojamiento:** la aplicación quedaría alojada en el sitio del clúster.
- **Entrega:** un producto mínimo viable en diciembre de 2026.
- **Alcance del producto mínimo viable:** solo la calculadora de Receptividad, en sectores de secano. Incluye registro e inicio de sesión, varios escenarios con su mapa, sectores y aguadas, campañas con sus datos, simulación, historial de campañas, guardado de cálculos, administración de los valores de referencia y una publicación en un host gratuito. Las otras tres calculadoras y lo que figura en "Para más adelante" quedan fuera.

## 2. Usuarios

- **Registro:** abierto. Cualquier persona puede crear una cuenta. Toda la aplicación, calculadoras incluidas, requiere iniciar sesión.
- **Rol:** cada usuario tiene un solo rol: productor, técnico o administrador. Todos se registran como productor. Nadie elige el rol al registrarse.
- **Primer administrador:** se crea con un comando que le da el rol a un usuario ya registrado. El rol técnico existe, pero por ahora no se asigna.
- **Productor y técnico:** por ahora ven y hacen lo mismo.
- **Administrador:** además, carga y corrige las tablas de referencia y los parámetros.

## 3. Organización de los datos

Los datos no pertenecen a ninguna calculadora. Viven en cuatro niveles, y las calculadoras los leen de ahí.

| Nivel | Qué es | Qué guarda |
|---|---|---|
| Escenario | El establecimiento: el campo entero, dividido en sectores. | Nombre, ubicación y si es el principal. |
| Sector (unidad productiva) | Una parte cercada del campo que se usa para cría, recría o engorde. No se subdivide. | Ambiente, polígono, superficie y aguadas. |
| Campaña | Un ciclo anual del establecimiento. | Fecha de inicio y de fin, y lluvia de la campaña anterior (opcional). |
| Rodeo de la campaña | Los animales de una unidad en una campaña. | Cantidad por categoría, período de entore, estado del campo, porcentajes de reposición y de destete, destete precoz, suplementación y condición corporal al parto. |

- **Categorías del rodeo:** el productor carga la cantidad de cada categoría de animal que tenga el sector: vacas, toros, vaquillonas, novillos de recría u otras. Las categorías salen de una tabla que mantiene el administrador. No hace falta indicar para qué se usa el sector.
- **Vaquillonas cargadas:** son las de más de un año. La pantalla lo aclara, para no contarlas dos veces con las terneras de reposición.
- **Terneros:** no se cargan. La aplicación calcula los terneros destetados y las terneras de reposición a partir de las vacas.
- **Rodeo por unidad:** el productor puede repartir su hacienda entre varias unidades. Cada cálculo se hace sobre el rodeo de esa unidad, no sobre el total del establecimiento.
- **Sector:** es la unidad mínima y no se subdivide. Cada parte del campo que el productor quiera calcular por separado se dibuja como un sector propio.
- **Precipitación de la campaña:** es la lluvia de la campaña anterior, en mm. Es opcional al guardar, pero la Receptividad la necesita para calcular.
- **Histórico:** un escenario acumula campañas. Las campañas anteriores no se modifican.
- **Meses de la campaña:** de julio a junio. El mes de inicio es un parámetro. El productor no carga fechas: elige el año.
- **Primera campaña:** se crea con el escenario. El productor elige el año: el actual o uno de los dos siguientes.
- **Campañas nuevas:** desde Mi campo solo se crean campañas de años posteriores. Nacen sin datos y no repiten año.
- **Campañas pasadas:** se cargan desde el historial, en "Cargá tu campaña".
- **Campaña actual:** la que contiene la fecha de hoy. Si ninguna la contiene, la más cercana.
- **Varios escenarios:** un usuario puede tener varios. La aplicación abre siempre el principal.

## 4. Campo y aguadas

- **Campo:** el productor dibuja el polígono de cada sector sobre un mapa.
- **Aguadas:** se marcan como puntos dentro del sector que abastecen. Una aguada fuera del sector no cuenta, aunque su alcance llegue al sector: los animales están encerrados en el sector y no llegan al agua.
- **Aguada compartida:** una aguada sobre el alambrado entre dos o más sectores puede abastecerlos a todos. Cada sector aprovecha la parte del alcance que cae dentro de él, y le tocan los litros en esa misma proporción. Por ejemplo, si el 70% del alcance cae en el sector 1, le toca el 70% del agua. El reparto se hace solo entre los sectores que comparten la aguada y sobre la parte del alcance que cae dentro de ellos.
- **Alcance de una aguada:** 2,5 km. Es un parámetro y se puede cambiar.
- **Superficie aprovechable:** la parte del polígono que queda dentro del alcance de alguna aguada del sector. Si los alcances se superponen, la superficie se cuenta una sola vez.
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

- **Dónde aplica:** sectores de secano.
- **Unidad de trabajo:** todo se expresa en equivalentes vaca (EV).
- **Receptividad:** se calcula con el método de Guevara y otros (IADIZA, 1995), a partir de la lluvia de la campaña anterior. Después se corrige por estado del campo, destete precoz y suplementación.
- **Datos que faltan:** si falta la lluvia o es 0, o si la superficie es 0, no se calcula y la aplicación avisa.
- **Otra lluvia:** si el año viene distinto, el productor puede simular con otra precipitación, mayor que 0, sin modificar sus datos.
- **Índices:** los de estado del campo, destete precoz y suplementación se multiplican entre sí. Destete precoz y suplementación se marcan con una casilla y su índice se aplica solo si está marcada. Si falta un índice, se calcula sin él y la aplicación avisa. Sus valores y dónde se guardan: Pendiente.
- **Límite por pasto:** superficie aprovechable dividida por la receptividad.
- **Composición del rodeo:** por cada vaca, los toros según toros por vaca, las terneras de reposición (vacas × porcentaje de reposición) y la misma cantidad de vaquillonas. Las vacas valen 1 EV todo el año. Los terneros que no son de reposición salen al destete y no cuentan. Las terneras de reposición no pueden superar a las hembras destetadas: si la reposición pide más, se acepta el dato y se avisa.
- **Calendario:** se arma desde el inicio del entore. El parto llega a los 283 días y el destete a los 6 meses, o a los 3 con destete precoz. Solo sirve para saber en qué estación están en el campo las terneras y las vaquillonas, para el agua.
- **Límite por agua:** litros por día que reponen las aguadas del sector, divididos por los litros por día que necesita en verano cada EV de la composición.
- **Sin dato de agua:** si solo algunas aguadas tienen litros, se calcula con esas y la aplicación avisa. Si ninguna tiene litros, o el sector no tiene vacas, se usa solo el límite por pasto y se aclara que el agua no se evaluó.
- **Rodeo máximo:** el menor entre el límite por pasto y el límite por agua. Se informa cuál de los dos limita.
- **Rodeo recomendado:** es el resultado principal. El rodeo máximo repartido según la composición, en cantidades enteras redondeadas al número más cercano, con al menos un toro. Si el rodeo entero se pasa del rodeo máximo o de los litros de verano, se bajan vacas hasta que entre. Si no entra una vaca con su toro, no se muestra y la aplicación avisa. Si el sector no tiene vacas, no se arma.
- **Mi rodeo ajustado:** el rodeo cargado, agrandado o achicado hasta el rodeo máximo, con sus mismas proporciones. Se toma la mayor cantidad entera de vacas que entra. Al menos un toro solo si se cargaron toros.
- **Termómetro de carga:** compara el rodeo actual con el rodeo máximo, sin redondear. El rodeo actual suma los animales cargados y las terneras de reposición que calcula la aplicación. Tiene tres estados: por debajo, dentro o por encima de la capacidad. El límite entre "por debajo" y "dentro" es un parámetro.
- **Necesidad de agua:** litros por día que necesita el límite por pasto, con la composición del rodeo, en verano y en invierno, frente a lo que reponen las aguadas.

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
| Consumo de agua de un animal adulto | 70 litros por día en verano y 35 a 40 en invierno | Clúster |
| Consumo de agua por categoría | Punto medio de cada rango de la tabla del clúster. Provisorio, a confirmar con una fuente local. | Clúster |
| Toros por vaca | 4,5 cada 100 vacas por defecto. El clúster indica de 4 a 5, y hasta 6 o 7 en el noreste; 4,5 es el punto medio elegido por el equipo. Es el único parámetro que el productor puede cambiar desde la calculadora. | Clúster |
| Consumo diario en corral | 3,5% del peso vivo | Clúster |
| Mes de inicio de la campaña | Julio | Equipo |
| Días de gestación | 283 | Falta citar la fuente |
| Edad al destete | 6 meses, o 3 con destete precoz | Equipo |
| Edad al primer entore de la vaquillona | 24 meses | Lámina de equivalencias |
| Hembras entre los terneros destetados | 50%. Valor redondo: estudios de otros países dan entre 50 y 53% de machos. No hay un dato medido en Mendoza. | Equipo |
| Meses de verano | Diciembre a febrero. Provisorio. | Equipo |
| Meses de invierno | Junio a agosto. Provisorio. | Equipo |
| Límite del termómetro entre "por debajo" y "dentro" | 90% del rodeo máximo. Provisorio. | Equipo |

El equivalente vaca incluye el consumo del ternero hasta los 6 meses.

**Consumo por categoría:** no se guarda. Se calcula como equivalencia en EV de la categoría × consumo anual de un EV, así que si cambia el consumo del EV cambian todas las categorías.

**Categorías cargadas.** Las equivalencias en EV y el agua son provisorias: las equivalencias son valores habituales que el clúster todavía no confirmó.

| Categoría | EV | Agua en verano (l/día) | Agua en invierno (l/día) |
|---|---|---|---|
| Vaca | 1,0 | 70 | 37,5 |
| Toro | 1,3 | 65 | 30 |
| Vaquillona | 0,7 | 42,5 | 20 |
| Ternero (destetado) | 0,5 | 25 | 12,5 |
| Novillo de recría | 0,8 | 42,5 | 20 |

Las terneras de reposición valen como ternero destetado (0,5 EV) desde el destete hasta el año, y las vaquillonas 0,7 EV desde el año hasta el primer entore. Su valor anual es su EV × los meses que pasa en la etapa ÷ 12.
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
| Mi campo | Escenario, sectores, mapa, aguadas y datos de la campaña. |
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
- **Idioma del código:** todo el código va en inglés: tablas, columnas, tipos enumerados y sus valores, variables, funciones, clases, archivos, rutas de la API y claves del JSON. En español van los comentarios, los docstrings y todo texto que lee una persona (mensajes de error, textos en pantalla, logs, descripciones de parámetros). Los términos del dominio se traducen siempre igual, según el glosario de `CLAUDE.md`.
- **Despliegue:** el desarrollo es local y el despliegue se hace al final.

## 14. Reglas del modelo de datos

- **Campañas:** dos campañas del mismo escenario no se pueden superponer en fechas.
- **Escenario principal:** cada usuario tiene uno solo. El primero que registra queda como principal, y puede marcar otro.
- **Rodeo de la campaña:** la campaña y la unidad productiva tienen que ser del mismo escenario. Hay un solo rodeo por unidad y por campaña.
- **Superficie de la unidad:** la calcula la base a partir del polígono. Nunca se carga a mano.
- **Porcentajes de reposición y de destete:** se guardan como fracción entre 0 y 1. En pantalla se muestran como porcentaje.
- **Período de entore:** se carga completo, con inicio y fin, o no se carga. El inicio y el fin caen dentro de la campaña.
- **Datos obligatorios con vacas:** porcentaje de reposición, porcentaje de destete y período de entore.
- **Aguadas:** cada aguada está dentro de su sector.
- **Condición corporal al parto:** entre 1 y 5.
- **Terneros:** no se cargan.

## 15. Forma de trabajo

- **Equipo:** tres desarrolladores y un scrum master.
- **Repositorio:** uno solo, con `backend/`, `frontend/` y `docs/`.
- **Ramas y pull requests:** según el `README.md` del repositorio.
- **Código:** se escribe con Claude Code, a partir de un documento de contexto con estas definiciones.

## 16. Para más adelante

- **Verificación del correo y recuperación de contraseña.**
- **Fin automático de la campaña:** al terminar, la campaña se cierra, pasa al historial y se crea la siguiente.
- **Lluvia mensual:** que el productor cargue cada mes y la aplicación sume el total de la campaña.
- **Vista del establecimiento completo:** el rodeo máximo total de todas las unidades frente al rodeo total.
- **Bajo riego y dieta por etapas:** se suman al modelo de datos cuando estén definidos.

## 17. Fuera de esta etapa

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
