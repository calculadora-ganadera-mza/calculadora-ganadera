# Cómo funciona cada calculadora

Calculadora ganadera · actualizado al 20 de octubre de 2026

Las decisiones generales (guardado, simulación, costos, ambientes) están en `definiciones-del-proyecto`. Los valores de referencia y su origen están en la sección 7 de ese documento.

Común a las cuatro:

- Todo el cálculo ocurre en el servidor.
- Cada calculadora arranca con los valores de la campaña y el productor los puede cambiar para simular.
- Cada cálculo guarda los valores de referencia con los que se hizo.

---

## Receptividad ganadera y tamaño del rodeo

**Qué responde:** cuántos animales puede mantener el campo, y cómo está la carga actual frente a ese máximo.

**Dónde aplica:** unidades de secano. No aplica a corral. En bajo riego, pendiente.

### Datos que usa

| Origen | Datos |
|---|---|
| Del escenario | Subzona, con su lluvia confiable. |
| Del mapa | Polígono de la unidad. Aguadas, con los litros que repone cada una por día (opcional). |
| De la campaña | Estado del campo. Cantidad por categoría de animal. Porcentaje de reposición. Porcentaje de destete. |
| Se carga en la calculadora | Tecnologías de manejo que aplica: suplementación, destete precoz. Toros por vaca. Precipitación, solo si se quiere simular otra lluvia. |
| Del sistema | Eficiencia de uso de la lluvia: 2,15 kg MS/ha/mm en herbáceas y 1,4 en leñosas. Forraje accesible: 80% de las herbáceas y 50% de las leñosas. Factor de uso: 30%. Consumo de un EV: 3.285 kg MS por año. Índice por estado del campo. Índice por tecnología de manejo. Alcance de las aguadas: 2,5 km. Equivalencias en EV y consumo de agua de cada categoría. |

### Cómo calcula

1. **Superficie aprovechable:** intersección entre el polígono y los círculos de 2,5 km alrededor de cada aguada. Las superposiciones se cuentan una sola vez.
2. **Forraje producido (kg MS por ha por año):** lluvia × 2,15 para herbáceas, y lluvia × 1,4 para leñosas. La lluvia es la confiable de la subzona, o la que cargue el productor si está simulando.
3. **Forraje disponible:** 80% de las herbáceas + 50% de las leñosas.
4. **Forraje consumible:** 30% del disponible.
5. **Receptividad base (ha por EV):** consumo anual de un EV ÷ forraje consumible.
6. **Receptividad corregida:** la base, corregida por el índice del estado del campo y el índice de cada tecnología de manejo elegida.
7. **Límite por pasto (EV):** superficie aprovechable ÷ receptividad corregida.
8. **Composición del límite por pasto:** el total en EV se reparte por categoría según toros por vaca, porcentaje de reposición, porcentaje de destete y las equivalencias de cada categoría.
9. **Necesidad de agua:** con esa composición, litros por día que necesita el rodeo, en verano y en invierno, sumando el consumo de cada categoría.
10. **Límite por agua (EV):** si las aguadas reponen un porcentaje de esa necesidad, el límite por agua es ese mismo porcentaje del límite por pasto. Se calcula para verano y para invierno.
11. **Rodeo máximo (EV):** el menor entre el límite por pasto y el límite por agua en verano. Se informa cuál de los dos limita.
12. **Rodeo actual (EV):** las cantidades de cada categoría de la campaña, convertidas con sus equivalencias.
13. **Termómetro de carga:** rodeo actual ÷ rodeo máximo, en porcentaje. Indica si la carga está por debajo, dentro o por encima de la capacidad.

Los pasos 2 a 5 resumen el método de Guevara y otros (1995). En la práctica dan 0,73 kg de MS consumible por hectárea por cada mm de lluvia.

Si no se cargaron los litros que reponen las aguadas, se omiten los pasos 9 y 10, el rodeo máximo es el límite por pasto y el resultado aclara que el agua no se evaluó.

### Qué devuelve

- Superficie aprovechable.
- Receptividad, en hectáreas por EV.
- Límite por pasto y límite por agua, en EV.
- Rodeo máximo, en EV, desglosado por categoría, y cuál de los dos límites lo fija.
- Necesidad de agua del rodeo frente a lo que reponen las aguadas, en verano y en invierno.
- Termómetro de carga.

### Pendientes

- Índices de corrección por estado del campo y por tecnología de manejo.
- Cómo se calcula en bajo riego.

---

## Proyección del estado del rodeo

**Qué responde:** si el pasto alcanza, período por período a lo largo del año, para mantener el rodeo y llevar a las vacas a la condición corporal buscada al entore.

**Dónde aplica:** unidades de secano que tienen vacas. No aplica a corral. En bajo riego, pendiente.

### Datos que usa

| Origen | Datos |
|---|---|
| Del escenario | Subzona, con su lluvia confiable. |
| Del mapa | Superficie aprovechable. |
| De la campaña | Cantidad por categoría de animal. Período de entore. Estado del campo. Condición corporal al parto. Porcentaje de destete del año anterior. |
| Se carga en la calculadora | Condición corporal buscada al entore. Precipitación, solo si se quiere simular otra lluvia. |
| Del sistema | Coeficientes del método de Guevara (los mismos de la Receptividad). Períodos forrajeros y porcentaje de producción de cada uno. Consumo de cada categoría. Consumo de una vaca vacía: 2.268 kg de MS por año. Consumo de una vaca con cría: 3.285 kg de MS por año. Gestación: 283 días. Equivalencia de condición corporal: medio punto = 15 kg. Umbrales del semáforo. |

### Cómo calcula

1. **Producción anual de pasto consumible:** con el mismo método de la Receptividad (lluvia confiable de la subzona, eficiencia de uso, forraje accesible y factor de uso del 30%), sobre la superficie aprovechable y corregida por el estado del campo.
2. **Oferta por período:** la producción anual se reparte según el porcentaje de cada período forrajero. Los períodos tienen resolución variable: cercana a mensual desde octubre o noviembre y cercana a trimestral desde mayo o junio.
3. **Calendario del rodeo:** desde el período de entore se ubican la preñez, el parto (inicio del entore + 283 días), la lactancia y el período vacío.
4. **Vacas con cría:** cantidad de vacas × porcentaje de destete del año anterior. El resto se considera vacío durante la lactancia.
5. **Demanda por período:** cantidad de vacas en cada estado × consumo de ese estado, más el consumo de las demás categorías de la unidad, proporcional a los días del período.
6. **Demanda extra por condición corporal:** diferencia entre la condición buscada al entore y la del parto, en medios puntos × 15 kg de peso por vaca, convertida en kilos de pasto y repartida entre el parto y el entore.
7. **Balance por período:** oferta − demanda.
8. **Período crítico y faltante:** los períodos con balance negativo y la suma de su faltante.
9. **Semáforo:** verde, amarillo o rojo, según el faltante del período más ajustado.

### Qué devuelve

- Semáforo.
- Período crítico y kilos de pasto faltantes.
- Oferta y demanda de cada período, para el gráfico.

### Pendientes

- Cortes de los períodos forrajeros y porcentaje de producción de cada uno, y si cambian por zona.
- Duración de la lactancia.
- Kilos de pasto por kilo de peso ganado, para la demanda extra.
- Consumo de vaquillonas de primera y de segunda parición.
- Umbrales del semáforo.

---

## Conveniencia económica del destete

**Qué responde:** el margen bruto de alimentar al ternero desde el destete hasta la venta.

**Dónde aplica:** cualquier unidad.

### Datos que usa

| Origen | Datos |
|---|---|
| Se carga en la calculadora | Peso al destete. Peso de venta. Precio de venta por kg. Precio al destete por kg. Precio del alimento por kg. Cantidad de alimento hasta la venta (opcional). Costos variables por rubro, valor por ternero (opcional). |
| Del sistema | Parámetros para estimar el alimento cuando no se carga. Listado de rubros de costos variables. |

### Cómo calcula

1. **Kilos ganados:** peso de venta − peso al destete.
2. **Alimento:** el que cargó el productor o, si no lo cargó, el estimado a partir de los kilos ganados.
3. **Costo del alimento:** alimento × precio del alimento.
4. **Costos variables:** suma de los rubros cargados.
5. **Valor de venta:** peso de venta × precio de venta.
6. **Valor al destete:** peso al destete × precio al destete.
7. **Margen bruto por ternero:** valor de venta − valor al destete − costo del alimento − costos variables.
8. **Margen bruto por kilo ganado:** margen por ternero ÷ kilos ganados.

### Qué devuelve

- Margen bruto por ternero y por kilo ganado.
- Detalle de ingresos y costos.
- Si el alimento fue cargado o estimado, y qué costos incluye.

### Pendientes

- Si se carga un solo precio del ternero o dos. Con un solo precio, los pasos 5 y 6 se reemplazan por kilos ganados × precio.
- Método para estimar el alimento: eficiencia de conversión o ración diaria.
- Listado de rubros de costos variables.

---

## Conveniencia de ganadería en corral

**Qué responde:** el margen bruto de un ciclo de engorde a corral.

**Dónde aplica:** cualquier unidad. Se puede guardar un cálculo por cada ciclo de la campaña.

**Modalidades:** corral propio y hotelería.

### Datos que usa

| Origen | Datos |
|---|---|
| Se carga en la calculadora | Modalidad. Peso de ingreso. Peso de salida. Ganancia diaria de peso. Porcentaje de grano en la dieta. Precio del maíz por kg. Precio del forraje por kg (opcional). Precio de ingreso por kg. Precio de egreso por kg. Costos variables por rubro, valor por animal (opcional). |
| Del sistema | Consumo diario de materia seca, en porcentaje del peso vivo. Listado de rubros de costos variables. |

### Cómo calcula

1. **Kilos a ganar:** peso de salida − peso de ingreso.
2. **Días de estadía:** kilos a ganar ÷ ganancia diaria.
3. **Consumo diario:** 3,5% × promedio entre peso de ingreso y peso de salida.
4. **Maíz por día:** consumo diario × porcentaje de grano. **Forraje por día:** el resto del consumo.
5. **Maíz y forraje del ciclo:** consumo por día × días de estadía.
6. **Costo del alimento:** maíz × precio del maíz + forraje × precio del forraje. Si no se cargó precio del forraje, se excluye y el resultado lo aclara.
7. **Valor al ingreso:** peso de ingreso × precio de ingreso. **Valor al egreso:** peso de salida × precio de egreso.
8. **Margen bruto por animal:** valor al egreso − valor al ingreso − costo del alimento − costos variables.
9. **Margen bruto por kilo producido:** margen por animal ÷ kilos a ganar.

### Qué devuelve

- Margen bruto por animal y por kilo producido.
- Días de estadía.
- Maíz y forraje del ciclo, con su costo.
- Diferencia entre el precio por kilo de ingreso y el de egreso.
- Qué costos incluye.

### Pendientes

- Porcentaje de grano de referencia.
- Etapas de la dieta: qué se carga en cada una.
- Cálculo en hotelería: qué conceptos cobra el feedlot y en qué unidades.
- Listado de rubros de costos variables.
