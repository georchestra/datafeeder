import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirCheckCircle,
  iconoirWarningTriangle,
  iconoirXmark
} from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { OperationToastStore } from '../../../core/stores/operation-toast.store'

marker('errors.operation.metadataSave')
marker('errors.operation.gnPublish')
marker('errors.operation.gnUnpublish')
marker('errors.operation.gnRightsEdit')
marker('errors.operation.gsRightsEdit')
marker('errors.operation.gsPublish')
marker('errors.operation.gsUnpublish')
marker('errors.operation.deletion')
marker('info.operation.metadataSave')

@Component({
  selector: 'app-operation-toast',
  imports: [NgIconComponent, TranslatePipe],
  templateUrl: './operation-toast.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    provideIcons({ iconoirWarningTriangle, iconoirXmark, iconoirCheckCircle })
  ]
})
export class OperationToastComponent {
  protected store = inject(OperationToastStore)

  dismiss(id: string): void {
    this.store.remove(id)
  }
}
