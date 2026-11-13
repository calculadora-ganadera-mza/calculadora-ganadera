/** Error con un mensaje del backend pensado para mostrar al usuario. */
export class ApiError extends Error {}

/** Error de una respuesta fallida, según el formato de errores del contrato. */
export async function responseError(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null)
  // Un detail de texto es un mensaje para el usuario; una lista es un error de formato
  if (typeof body?.detail === 'string') return new ApiError(body.detail)
  return new Error(`Error ${response.status}`)
}
