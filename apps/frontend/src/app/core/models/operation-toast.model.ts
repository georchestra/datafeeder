import { HttpErrorResponse } from '@angular/common/http'

export type ToastError = HttpErrorResponse | Error

export interface OperationToast {
  id: string
  translationKey: string
  type: 'error' | 'info' | 'ai'
  customIcon?: string
  customColor?: 'primary' | 'secondary'
}
