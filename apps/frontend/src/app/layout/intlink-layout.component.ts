import { Component, inject, signal } from '@angular/core'
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirFloppyDisk, iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  EditorFacade,
  findConverterForDocument,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import { finalize, from, switchMap, take, withLatestFrom } from 'rxjs'
import { Api } from '../core/api/api'
import { updateMetadataGnIngestionIntegrityLinkIntegrityLinkIdMetadataGnPut } from '../core/api/functions'
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

  isSaving = signal<boolean>(false)

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
