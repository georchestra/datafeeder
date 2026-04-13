import { Component, inject, signal } from '@angular/core'
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirFloppyDisk, iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import {
  ConfirmationDialogComponent,
  EditorFacade,
  RecordsRepositoryInterface,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import { MatDialog } from '@angular/material/dialog'
import { finalize, firstValueFrom, switchMap, take, withLatestFrom } from 'rxjs'
import { Api } from '../core/api/api'
import {
  deleteScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet
} from '../core/api/functions'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { ErrorToastStore } from '../core/stores/error-toast.store'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'

marker('intlinkLayout.error.forbidden.message')
marker('intlinkLayout.error.forbidden.title')
marker('intlinkLayout.error.not_found.message')
marker('intlinkLayout.error.not_found.title')
marker('intlinkLayout.error.server_error.message')
marker('intlinkLayout.error.server_error.title')
marker('sidebar.reconfigureDataset.warning')
marker('sidebar.reconfigureDataset.warningActiveRun')
marker('sidebar.reconfigureDataset.warningTitle')

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
  private errorToastStore = inject(ErrorToastStore)
  private router = inject(Router)
  private matDialog = inject(MatDialog)
  private translate = inject(TranslateService)
  private api = inject(Api)

  isSaving = signal<boolean>(false)

  async onReconfigureClick(): Promise<void> {
    const intlink = this.store.integrityLink()
    const intlinkId = this.store.intlinkId()
    if (!intlink || !intlinkId) return

    if (intlink.schedule_enabled) {
      const runs = await this.api.invoke(
        getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
        { dag_id: 'process_dag', intlink_id: intlinkId }
      )
      const hasActiveRun = runs.dag_runs.some(
        (r) => r.state === 'running' || r.state === 'queued'
      )
      const messageKey = hasActiveRun
        ? 'sidebar.reconfigureDataset.warningActiveRun'
        : 'sidebar.reconfigureDataset.warning'

      const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
        data: {
          title: this.translate.instant('sidebar.reconfigureDataset.warningTitle'),
          message: this.translate.instant(messageKey),
          confirmText: this.translate.instant('common.continue'),
          cancelText: this.translate.instant('common.cancel'),
          focusCancel: 'cancel',
        },
      })
      const confirmed = await firstValueFrom(dialogRef.afterClosed())
      if (!confirmed) return

      await this.api.invoke(
        deleteScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
        { integrity_link_id: intlinkId }
      )
    }

    this.router.navigate(['/import', intlinkId])
  }

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
          this.errorToastStore.add('metadataSave')
        }
      })
  }
}
