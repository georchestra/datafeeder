import { Injectable, signal } from '@angular/core'
import { HttpErrorResponse } from '@angular/common/http'
import { ErrorToast } from '../models/error-toast.model'

@Injectable({ providedIn: 'root' })
export class ErrorToastStore {
  toasts = signal<ErrorToast[]>([])

  add(operationKey: string, error?: unknown): void {
    let translationKey: string
    if (
      error instanceof HttpErrorResponse &&
      typeof error.error?.detail === 'string'
    ) {
      translationKey = error.error.detail
    } else {
      translationKey = `errors.operation.${operationKey}`
    }
    const id = crypto.randomUUID()
    this.toasts.update((toasts) => [...toasts, { id, translationKey }])
  }

  remove(id: string): void {
    this.toasts.update((toasts) => toasts.filter((t) => t.id !== id))
  }
}
