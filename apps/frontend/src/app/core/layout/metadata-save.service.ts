import { inject, Injectable, signal, Signal } from '@angular/core'
import { firstValueFrom, combineLatest } from 'rxjs'
import { EditorFacade, findConverterForDocument } from 'geonetwork-ui'
import { Api } from '../api/api'
import { updateMetadataGnIngestionIntegrityLinkIntegrityLinkIdMetadataGnPut } from '../api/functions'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { OperationToastStore } from '../stores/operation-toast.store'

@Injectable({ providedIn: 'root' })
export class MetadataSaveService {
  private editor = inject(EditorFacade)
  private api = inject(Api)
  private store = inject(IntegrityLinkStore)
  private operationToastStore = inject(OperationToastStore)

  private readonly _isSaving = signal<boolean>(false)
  readonly isSaving: Signal<boolean> = this._isSaving.asReadonly()

  async save(): Promise<void> {
    if (this._isSaving()) return

    const integrityLink = this.store.integrityLink()
    if (!integrityLink) return

    this._isSaving.set(true)
    try {
      const [record, recordSource] = await firstValueFrom(
        combineLatest([this.editor.record$, this.editor.recordSource$])
      )
      const serializedXml = await findConverterForDocument(
        recordSource
      ).writeRecord(record, recordSource)
      const updated = await this.api.invoke(
        updateMetadataGnIngestionIntegrityLinkIntegrityLinkIdMetadataGnPut,
        {
          integrity_link_id: integrityLink.id,
          body: { serialized_xml: serializedXml, title: record.title }
        }
      )
      this.store.integrityLink.update((current) => ({
        ...current!,
        integrity_title: updated.integrity_title
      }))
      this.operationToastStore.addInfo('metadataSave')
    } catch (error) {
      this.operationToastStore.addError('metadataSave')
      throw error
    } finally {
      this._isSaving.set(false)
    }
  }
}
