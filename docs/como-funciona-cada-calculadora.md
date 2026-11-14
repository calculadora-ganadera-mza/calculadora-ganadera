# Cómo funciona cada calculadora

Calculadora ganadera · actualizado al 14 de noviembre de 2026

Las decisiones generales (guardado, simulación, costos, ambientes) están en `definiciones-del-proyecto`. Los valores de referencia y su origen están en la sección 7 de ese documento.

Común a las cuatro:

- Todo el cálculo ocurre en el servidor.
- Cada calculadora arranca con los valores de la campaña y el productor los puede cambiar para simular.
- Cada cálculo guarda los valores de referencia con los que se hizo.

---

## Receptividad ganadera y tamaño del rodeo

**Qué responde:** cuántos animales puede mantener el sector, qué rodeo conviene tener y cómo está la carga actual frente a ese máximo.

**Dónde aplica:** sectores de secano. No aplica a corral. En bajo riego, pendiente.

### Datos que usa

| Origen | Datos |
|---|---|
| Del mapa | Polígono del sector. Aguadas del sector y aguadas compartidas con sectores vecinos, con los litros que repone cada una por día (opcional). |
| De la campaña | Lluvia de la campaña anterior. Estado del campo. Cantidad por categoría de animal. Porcentaje de reposición. Porcentaje de destete. Inicio del entore. Destete precoz y suplementación, marcados o no. |
| Se carga en la calculadora | Solo para simular: los datos de la campaña y los toros por vaca. La superficie y las aguadas siempre salen del mapa. |
| Del sistema | Eficiencia de uso de la lluvia: 2,15 kg MS/ha/mm en herbáceas y 1,4 en leñosas. Forraje accesible: 80% de las herbáceas y 50% de las leñosas. Factor de uso: 30%. Consumo de un EV: 3.285 kg MS por año. Índices por estado del campo, destete precoz y suplementación. Alcance de las aguadas: 2,5 km. Equivalencias en EV y consumo de agua de cada categoría. Toros por vaca: 4,5 cada 100. Gestación: 283 días. Edad al destete: 6 meses, o 3 con destete precoz. Edad al primer entore: 24 meses. Hembras entre los terneros destetados: 50%. Meses de verano y de invierno. Límite del termómetro: 90%. |

### Cómo calcula

1. **Superficie aprovechable:** intersección entre el polígono y los círculos de 2,5 km alrededor de las aguadas del sector y de las compartidas con él. Las superposiciones se cuentan una sola vez.
2. **Forraje producido (kg MS por ha por año):** lluvia × 2,15 para herbáceas, y lluvia × 1,4 para leñosas. La lluvia es la de la campaña anterior, o la que cargue el productor si está simulando.
3. **Forraje disponible:** 80% de las herbáceas + 50% de las leñosas.
4. **Forraje consumible:** 30% del disponible.
5. **Receptividad base (ha por EV):** consumo anual de un EV ÷ forraje consumible.
6. **Receptividad corregida:** la base, corregida por los índices de estado del campo, destete precoz y suplementación, multiplicados entre sí. Los de destete precoz y suplementación se aplican solo si están marcados.
7. **Límite por pasto (EV):** superficie aprovechable ÷ receptividad corregida.
8. **Composición por vaca:** lo que acompaña a cada vaca, en cabezas y en EV:
   - Vaca: 1 EV todo el año.
   - Toros: toros por vaca, con la equivalencia del toro.
   - Terneras de reposición: porcentaje de reposición, sin superar las hembras destetadas (porcentaje de destete × 50%). Valen 0,5 EV desde el destete hasta el año de edad: 6 de los 12 meses con destete normal y 9 con destete precoz.
   - Vaquillonas: la misma cantidad que las terneras de reposición. Valen 0,7 EV desde el año hasta el primer entore, a los 24 meses.
   - El valor anual de las terneras y las vaquillonas es su EV × los meses que pasan en la etapa ÷ 12. Los terneros que no son de reposición salen al destete y no cuentan.
9. **Calendario:** el parto es el inicio del entore + 283 días, y el destete llega 6 meses después del parto, o 3 con destete precoz. Las terneras están en el campo desde el destete hasta el año, y las vaquillonas desde el año hasta el primer entore. El calendario se repite todos los años.
10. **Litros por EV en verano:** litros por día que necesita en verano la composición por vaca, sumando cada categoría por cabeza, ÷ los EV de esa composición. Las terneras y las vaquillonas cuentan solo si están en el campo en algún mes del verano.
11. **Litros disponibles:** los litros por día de las aguadas del sector, más la parte que le toca de cada aguada compartida. La parte es la misma proporción del alcance que cae en el sector, calculada solo entre los sectores que comparten la aguada.
12. **Límite por agua (EV):** litros disponibles ÷ litros por EV en verano.
13. **Rodeo máximo (EV):** el menor entre el límite por pasto y el límite por agua. Se informa cuál de los dos limita.
14. **Rodeo recomendado:** el rodeo máximo repartido según la composición por vaca, en cantidades enteras redondeadas al número más cercano, con al menos un toro. Si el rodeo entero supera el rodeo máximo o los litros disponibles en verano, se baja una vaca por vez hasta que entre. Se informan también los terneros destetados, machos y hembras.
15. **Rodeo actual (EV):** las cantidades cargadas, convertidas con sus equivalencias, más las terneras de reposición que se calculan a partir de las vacas, con su valor anual.
16. **Mi rodeo ajustado:** el rodeo actual agrandado o achicado hasta el rodeo máximo, con sus mismas proporciones. Se toma la mayor cantidad entera de vacas que entra y el resto sale de las proporciones cargadas. Lleva al menos un toro solo si se cargaron toros.
17. **Termómetro de carga:** rodeo actual ÷ rodeo máximo, sin redondear. Por debajo de 90% la carga está por debajo de la capacidad, hasta 100% está dentro y si supera 100% está por encima.
18. **Necesidad de agua:** litros por día que necesita el límite por pasto con la composición por vaca, en verano y en invierno, frente a los litros disponibles. Las terneras y las vaquillonas cuentan solo en la estación en que están en el campo.

Los pasos 2 a 5 resumen el método de Guevara y otros (1995). En la práctica dan 0,73 kg de MS consumible por hectárea por cada mm de lluvia. Sin índices, con 300 mm de lluvia la receptividad es de 15,1 ha por EV.

**Casos especiales:**

- Si falta la lluvia o es 0, o si la superficie aprovechable es 0, no se calcula y la aplicación avisa.
- Si falta un índice, se calcula sin él y la aplicación avisa.
- Si las terneras de reposición superan a las hembras destetadas, se acepta el dato, se cuentan las hembras destetadas y la aplicación avisa.
- Si solo algunas aguadas tienen litros, se calcula con esas y la aplicación avisa.
- Si ninguna aguada tiene litros, se omiten los pasos 10 a 12. El rodeo máximo es el límite por pasto y el resultado aclara que el agua no se evaluó.
- Si el sector no tiene vacas, no se arma la composición ni el rodeo recomendado. El rodeo máximo es el límite por pasto y el resultado aclara que el agua no se evaluó.
- Si el rodeo máximo no alcanza para una vaca con su toro, no se muestra el rodeo recomendado y la aplicación avisa. Los límites, el rodeo máximo y el termómetro se muestran igual.

### Qué devuelve

- Superficie aprovechable.
- Receptividad, en hectáreas por EV.
- Límite por pasto y límite por agua, en EV.
- Rodeo máximo, en EV, y cuál de los dos límites lo fija.
- Rodeo recomendado, en cabezas por categoría, con los terneros destetados machos y hembras.
- Mi rodeo ajustado, en cabezas por categoría.
- Termómetro de carga: su estado y los dos números que compara, rodeo actual y rodeo máximo.
- Necesidad de agua frente a los litros disponibles, en verano y en invierno.
- Los avisos de los casos especiales.

### Pendientes

- Valores de los índices por estado del campo, destete precoz y suplementación, y dónde se guardan.
- Fuente de los 283 días de gestación.
- Meses de verano y de invierno, límite del termómetro y consumo de agua por categoría: son provisorios.
- Cómo se calcula en bajo riego.

---

## Proyección del estado del rodeo

**Qué responde:** si el pasto alcanza, período por período a lo largo del año, para mantener el rodeo y llevar a las vacas a la condición corporal buscada al entore.

**Dónde aplica:** unidades de secano que tienen vacas. No aplica a corral. En bajo riego, pendiente.

### Datos que usa

| Origen | Datos |
|---|---|
| Del mapa | Superficie aprovechable. |
| De la campaña | Lluvia de la campaña anterior. Cantidad por categoría de animal. Período de entore. Estado del campo. Condición corporal al parto. Porcentaje de destete del año anterior. |
| Se carga en la calculadora | Condición corporal buscada al entore. Precipitación, solo si se quiere simular otra lluvia. |
| Del sistema | Coeficientes del método de Guevara (los mismos de la Receptividad). Períodos forrajeros y porcentaje de producción de cada uno. Consumo de cada categoría. Consumo de una vaca vacía: 2.268 kg de MS por año. Consumo de una vaca con cría: 3.285 kg de MS por año. Gestación: 283 días. Equivalencia de condición corporal: medio punto = 15 kg. Umbrales del semáforo. |

### Cómo calcula

1. **Producción anual de pasto consumible:** con el mismo método de la Receptividad (lluvia de la campaña anterior, eficiencia de uso, forraje accesible y factor de uso del 30%), sobre la superficie aprovechable y corregida por el estado del campo.
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
