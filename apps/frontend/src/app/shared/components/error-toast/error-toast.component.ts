import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirWarningTriangle, iconoirXmark } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'

marker('errors.operation.metadataSave')
marker('errors.operation.gnPublish')
marker('errors.operation.gnUnpublish')
marker('errors.operation.gnRightsEdit')
marker('errors.operation.gsRightsEdit')
marker('errors.operation.gsPublish')
marker('errors.operation.gsUnpublish')
marker('errors.operation.deletion')
marker('errors.operation.loadPresets')
marker('errors.operation.updateSchedule')

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
