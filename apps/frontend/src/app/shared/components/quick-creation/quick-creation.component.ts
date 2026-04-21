import {
  ChangeDetectionStrategy,
  Component,
  inject,
  output,
  signal
} from '@angular/core'
import { Router } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirMoreHoriz, iconoirPlus } from '@ng-icons/iconoir'
import { Api } from '../../../core/api/api'
import { createEmptyDatasetIngestionIntegrityLinkEmptyPost } from '../../../core/api/functions'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'

marker('quickImport.modeWithData')
marker('quickImport.modeEmpty')
marker('errors.operation.emptyDatasetCreate')

@Component({
  selector: 'app-quick-creation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe, NgIconComponent],
  templateUrl: './quick-creation.component.html',
  providers: [provideIcons({ iconoirPlus, iconoirMoreHoriz })]
})
export class QuickCreationComponent {
  private readonly api = inject(Api)
  private readonly router = inject(Router)
  private readonly errorToastStore = inject(ErrorToastStore)

  datasetCreated = output<void>()

  isMenuOpen = signal(false)
  submitting = signal(false)

  navigateToImport() {
    this.router.navigate(['/', 'import'])
  }

  toggleMenu() {
    if (!this.submitting()) {
      this.isMenuOpen.update((v) => !v)
    }
  }

  closeMenu() {
    if (!this.submitting()) {
      this.isMenuOpen.set(false)
    }
  }

  async createEmptyDataset() {
    if (this.submitting()) return
    this.submitting.set(true)
    try {
      const result = await this.api.invoke(
        createEmptyDatasetIngestionIntegrityLinkEmptyPost,
        { body: {} }
      )
      this.datasetCreated.emit()
      this.router.navigate(['/', String(result.id), 'edit'])
    } catch (error) {
      this.errorToastStore.add('emptyDatasetCreate', error)
    } finally {
      this.submitting.set(false)
      this.isMenuOpen.set(false)
    }
  }
}
