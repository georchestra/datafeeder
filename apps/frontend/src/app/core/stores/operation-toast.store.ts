import { Injectable, signal } from '@angular/core'
import { OperationToast, ToastError } from '../models/operation-toast.model'
import { errorDetailKey } from '../http/http-error.util'

const TOAST_AUTO_DISMISS_MS = 5000

@Injectable({ providedIn: 'root' })
export class OperationToastStore {
  toasts = signal<OperationToast[]>([])

  addError(operationKey: string, error?: ToastError): void {
    this.add(errorDetailKey(error, `errors.operation.${operationKey}`), 'error')
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
