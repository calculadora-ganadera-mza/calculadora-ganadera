// Formatos de número para mostrar en pantalla, con coma decimal y punto de miles

// Siempre con un decimal: 15,1 o 60,0
export const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

// Hasta un decimal, sin ceros de más: 15,1 o 60
export const upToOneDecimal = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

// Sin decimales: 4.200
export const integer = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
