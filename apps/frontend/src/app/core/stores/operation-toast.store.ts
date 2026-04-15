import { Injectable, signal } from '@angular/core'
import { HttpErrorResponse } from '@angular/common/http'
import { OperationToast, ToastError } from '../models/operation-toast.model'

const TOAST_AUTO_DISMISS_MS = 5000

@Injectable({ providedIn: 'root' })
export class OperationToastStore {
  toasts = signal<OperationToast[]>([])

  addError(operationKey: string, error?: ToastError): void {
    let translationKey: string
    if (
      error instanceof HttpErrorResponse &&
      typeof error.error?.detail === 'string'
    ) {
      translationKey = error.error.detail
    } else {
      translationKey = `errors.operation.${operationKey}`
    }
    this.add(translationKey, 'error')
  }

  addInfo(operationKey: string): void {
    this.add(`info.operation.${operationKey}`, 'info')
  }

  remove(id: string): void {
    this.toasts.update((toasts) => toasts.filter((t) => t.id !== id))
  }

  private add(translationKey: string, type: 'error' | 'info'): void {
    const id = globalThis.crypto.randomUUID()
    this.toasts.update((toasts) => [...toasts, { id, translationKey, type }])
    globalThis.setTimeout(() => this.remove(id), TOAST_AUTO_DISMISS_MS)
  }
}
