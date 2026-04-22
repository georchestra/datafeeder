import { Component, inject, signal } from '@angular/core'
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirFloppyDisk, iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import {
  ConfirmationDialogComponent,
  EditorFacade,
  findConverterForDocument,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import { MatDialog } from '@angular/material/dialog'
import { finalize, firstValueFrom, from, switchMap, take, withLatestFrom } from 'rxjs'
import { Api } from '../core/api/api'
import {
  deleteIntegrityLinkScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  updateMetadataGnIngestionIntegrityLinkIntegrityLinkIdMetadataGnPut
} from '../core/api/functions'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { OperationToastStore } from '../core/stores/operation-toast.store'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'

marker('intlinkLayout.error.forbidden.message')
marker('intlinkLayout.error.forbidden.title')
marker('intlinkLayout.error.not_found.message')
marker('intlinkLayout.error.not_found.title')
marker('intlinkLayout.error.server_error.message')
marker('intlinkLayout.error.server_error.title')
marker('info.operation.metadataSave')
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
  private api = inject(Api)
  private operationToastStore = inject(OperationToastStore)
  private router = inject(Router)
  private matDialog = inject(MatDialog)
  private translate = inject(TranslateService)

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
          title: this.translate.instant(
            'sidebar.reconfigureDataset.warningTitle'
          ),
          message: this.translate.instant(messageKey),
          confirmText: this.translate.instant('common.continue'),
          cancelText: this.translate.instant('common.cancel'),
          focusCancel: 'cancel'
        }
      })
      const confirmed = await firstValueFrom(dialogRef.afterClosed())
      if (!confirmed) return

      await this.api.invoke(
        deleteIntegrityLinkScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
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
          from(
            findConverterForDocument(recordSource).writeRecord(
              record,
              recordSource
            )
          ).pipe(
            switchMap((serializedXml) =>
              from(
                this.api.invoke(
                  updateMetadataGnIngestionIntegrityLinkIntegrityLinkIdMetadataGnPut,
                  {
                    integrity_link_id: this.store.integrityLink()!.id,
                    body: { serialized_xml: serializedXml, title: record.title }
                  }
                )
              )
            )
          )
        ),
        finalize(() => {
          this.isSaving.set(false)
        })
      )
      .subscribe({
        next: (updatedIntlink) => {
          this.store.integrityLink.update((current) => ({
            ...current!,
            integrity_title: updatedIntlink.integrity_title
          }))
          this.operationToastStore.addInfo('metadataSave')
        },
        error: () => {
          this.operationToastStore.addError('metadataSave')
        }
      })
  }
}
