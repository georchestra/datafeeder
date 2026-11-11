import { HttpErrorResponse } from '@angular/common/http'

/**
 * Translation key of a failed request: the backend `detail` when it is a
 * non-empty string, else *fallbackKey* (a request validation error has a list).
 */
export function errorDetailKey(error: unknown, fallbackKey: string): string {
  const detail: unknown =
    error instanceof HttpErrorResponse ? error.error?.detail : undefined
  return typeof detail === 'string' && detail ? detail : fallbackKey
}
