import { Component, input, output, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirEye, iconoirEyeClosed } from '@ng-icons/iconoir'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { TranslatePipe } from '@ngx-translate/core'

marker('input.password.hide')
marker('input.password.show')

@Component({
  selector: 'app-ui-input-password',
  imports: [CommonModule, NgIconComponent, TranslatePipe],
  templateUrl: './ui-input-password.component.html',
  styleUrls: ['./ui-input-password.component.scss'],
  providers: [
    provideIcons({
      iconoirEye,
      iconoirEyeClosed
    })
  ]
})
export class UiInputPasswordComponent {
  value = input<string>('')
  placeholder = input<string>('')
  valueChange = output<string>()

  showPassword = signal(false)

  togglePasswordVisibility(): void {
    this.showPassword.update((show) => !show)
  }

  onInput(event: Event): void {
    const target = event.target as HTMLInputElement
    this.valueChange.emit(target.value)
  }
}
