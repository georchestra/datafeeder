import { HttpErrorResponse } from '@angular/common/http'
import { errorDetailKey } from './http-error.util'

describe('errorDetailKey', () => {
  const httpError = (error: unknown) =>
    new HttpErrorResponse({ error, status: 400 })

  it('should return the backend detail when it is a string', () => {
    expect(
      errorDetailKey(httpError({ detail: 'some.backend.key' }), 'fallback')
    ).toBe('some.backend.key')
  })

  it.each([
    ['a list detail', httpError({ detail: [{ msg: 'Field required' }] })],
    ['an empty detail', httpError({ detail: '' })],
    ['no body', httpError(null)],
    ['a non HTTP error', new Error('boom')]
  ])('should return the fallback key for %s', (_, error) => {
    expect(errorDetailKey(error, 'fallback')).toBe('fallback')
  })
})
