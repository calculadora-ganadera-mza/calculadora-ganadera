import { describe, expect, it } from 'vitest'

import { ApiError, responseError } from '../errors'

const response = (status: number, body: unknown) => new Response(JSON.stringify(body), { status })

describe('responseError', () => {
  it('un detail de texto es un ApiError con ese mensaje', async () => {
    const error = await responseError(response(409, { detail: 'Ya existe.' }))

    expect(error).toEqual(new ApiError('Ya existe.'))
  })

  it('un detail en lista es un error de formato que no se muestra', async () => {
    const error = await responseError(response(422, { detail: [{ msg: 'x' }] }))

    expect(error).not.toBeInstanceOf(ApiError)
    expect(error.message).toBe('Error 422')
  })

  it('una respuesta sin JSON también da un error', async () => {
    const error = await responseError(new Response('caído', { status: 502 }))

    expect(error.message).toBe('Error 502')
  })
})
