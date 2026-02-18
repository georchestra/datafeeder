import { Component, input, output } from '@angular/core'
import { NgClass } from '@angular/common'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirWarningTriangle,
  iconoirInfoCircle,
  iconoirCheckCircle,
  iconoirXmarkCircle
} from '@ng-icons/iconoir'
import { ButtonComponent } from 'geonetwork-ui'

export type AlertType = 'error' | 'warning' | 'info' | 'success'

@Component({
  selector: 'app-ui-alert-box',
  imports: [NgClass, NgIconComponent, ButtonComponent],
  templateUrl: './ui-alert-box.component.html',
  styleUrls: ['./ui-alert-box.component.scss'],
  providers: [
    provideIcons({
      iconoirWarningTriangle,
      iconoirInfoCircle,
      iconoirCheckCircle,
      iconoirXmarkCircle
    })
  ]
})
export class UiAlertBoxComponent {
  type = input<AlertType>('error')
  title = input<string>('')
  message = input<string>('')
  dismissible = input<boolean>(true)

  dismissed = output<void>()

  get iconName(): string {
    const icons: Record<AlertType, string> = {
      error: 'iconoirWarningTriangle',
      warning: 'iconoirWarningTriangle',
      info: 'iconoirInfoCircle',
      success: 'iconoirCheckCircle'
    }
    return icons[this.type()]
  }

  get containerClasses(): string {
    const classes: Record<AlertType, string> = {
      error: 'bg-red-50 border-red-600',
      warning: 'bg-orange-200 border-red-600',
      info: 'bg-blue-50 border-blue-600',
      success: 'bg-green-50 border-green-600'
    }
    return classes[this.type()]
  }

  get iconClasses(): string {
    const classes: Record<AlertType, string> = {
      error: 'text-red-600',
      warning: 'text-red-600',
      info: 'text-blue-600',
      success: 'text-green-600'
    }
    return classes[this.type()]
  }

  onDismiss(): void {
    this.dismissed.emit()
  }
}
