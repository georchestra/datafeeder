import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirWarningTriangle, iconoirXmark } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'

@Component({
  selector: 'app-error-toast',
  imports: [NgIconComponent, TranslatePipe],
  templateUrl: './error-toast.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [provideIcons({ iconoirWarningTriangle, iconoirXmark })]
})
export class ErrorToastComponent {
  protected store = inject(ErrorToastStore)

  dismiss(id: string): void {
    this.store.remove(id)
  }
}
