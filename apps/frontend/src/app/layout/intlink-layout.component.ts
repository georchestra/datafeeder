import { Component, inject, signal } from '@angular/core'
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirFloppyDisk, iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  EditorFacade,
  RecordsRepositoryInterface,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import { finalize, switchMap, take, withLatestFrom } from 'rxjs'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'

marker('intlinkLayout.error.forbidden.message')
marker('intlinkLayout.error.forbidden.title')
marker('intlinkLayout.error.not_found.message')
marker('intlinkLayout.error.not_found.title')
marker('intlinkLayout.error.server_error.message')
marker('intlinkLayout.error.server_error.title')

@Component({
  selector: 'app-intlink-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    NgIconComponent,
    TranslatePipe,
    UiAlertBoxComponent,
    SpinningLoaderComponent
  ],
  templateUrl: './intlink-layout.component.html',
  providers: [
    provideIcons({
      iconoirFloppyDisk,
      iconoirRefreshCircle
    })
  ]
})
export class IntlinkLayoutComponent {
  readonly store = inject(IntegrityLinkStore)

  private editor = inject(EditorFacade)
  private recordsRepository = inject(RecordsRepositoryInterface)

  isSaving = signal<boolean>(false)

  saveEdits(): void {
    if (this.isSaving()) return

    this.isSaving.set(true)
    this.editor.record$
      .pipe(
        withLatestFrom(this.editor.recordSource$),
        take(1),
        switchMap(([record, recordSource]) =>
          this.recordsRepository.saveRecord(record, recordSource, false)
        ),
        finalize(() => {
          this.isSaving.set(false)
        })
      )
      .subscribe({
        next: () => {
          //TODO: show success message
          console.log('Edits saved successfully')
        },
        error: () => {
          //TODO: show error message
          console.log('Failed to save edits')
        }
      })
  }
}
