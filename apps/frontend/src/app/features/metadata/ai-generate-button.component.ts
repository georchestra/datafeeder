import { Component, inject, input, signal } from '@angular/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirSparks } from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { MatDialog } from '@angular/material/dialog'
import {
  ConfirmationDialogComponent,
  type CatalogRecord,
  EditorFacade
} from 'geonetwork-ui'
import { firstValueFrom } from 'rxjs'
import { toSignal } from '@angular/core/rxjs-interop'
import { Api } from '../../core/api/api'
import { generateMetadataForIntegrityLinkLlmGenerateMetadataIntlinkIdPost } from '../../core/api/functions'
import { LlmMetadataDataSource } from '../../core/api/models/llm-metadata-data-source'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('footer.ai.regenerate')
marker('metadata.ai.confirmOverwrite.title')
marker('metadata.ai.confirmOverwrite.message')
marker('metadata.ai.confirmOverwrite.confirm')
marker('metadata.ai.confirmOverwrite.cancel')
marker('errors.operation.aiMetadataGeneration')
marker('info.operation.aiMetadataGeneration')

const LLM_METADATA_DATA_SOURCE_FINAL: LlmMetadataDataSource = 'final'

@Component({
  selector: 'app-ai-generate-button',
  imports: [NgIconComponent, TranslatePipe],
  templateUrl: './ai-generate-button.component.html',
  providers: [
    provideIcons({
      iconoirSparks
    })
  ]
})
export class AiGenerateButtonComponent {
  private api = inject(Api)
  private editor = inject(EditorFacade)
  private store = inject(IntegrityLinkStore)
  private matDialog = inject(MatDialog)
  private translate = inject(TranslateService)
  private operationToastStore = inject(OperationToastStore)

  isGeneratingAI = signal(false)
  disabled = input(false)
  lastAiMode = signal<'regenerate' | 'rewrite'>('rewrite')

  private changedSinceSave = toSignal(this.editor.changedSinceSave$, {
    initialValue: false
  })

  async onGenerateWithAI(
    mode: 'regenerate' | 'rewrite' = 'regenerate',
    extraContext?: string
  ): Promise<void> {
    this.lastAiMode.set(mode)
    const intlinkId = this.store.intlinkId()
    if (!intlinkId) {
      console.error('No integrity link ID available')
      return
    }

    if (this.changedSinceSave()) {
      const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
        data: {
          title: this.translate.instant('metadata.ai.confirmOverwrite.title'),
          message: this.translate.instant(
            'metadata.ai.confirmOverwrite.message'
          ),
          confirmText: this.translate.instant(
            'metadata.ai.confirmOverwrite.confirm'
          ),
          cancelText: this.translate.instant(
            'metadata.ai.confirmOverwrite.cancel'
          ),
          focusCancel: 'cancel'
        }
      })
      const confirmed = await firstValueFrom(dialogRef.afterClosed())
      if (!confirmed) return
    }

    this.isGeneratingAI.set(true)

    try {
      const currentRecord: CatalogRecord | null = (await firstValueFrom(
        this.editor.record$
      )) as CatalogRecord | null

      // Send ALL current values as context for the LLM.
      const currentValues: Record<string, string> = {}
      if (currentRecord) {
        if (currentRecord.title) currentValues['title'] = currentRecord.title
        if (currentRecord.abstract)
          currentValues['abstract'] = currentRecord.abstract
        if (currentRecord.keywords?.length)
          currentValues['keywords'] = currentRecord.keywords
            .map((k: { label: string }) => k.label)
            .join(', ')
        if (currentRecord.topics?.length)
          currentValues['topics'] = (currentRecord.topics as string[]).join(
            ', '
          )
      }

      const generatedMetadata = await this.api.invoke(
        generateMetadataForIntegrityLinkLlmGenerateMetadataIntlinkIdPost,
        {
          intlink_id: intlinkId,
          body: {
            mode,
            current_values: Object.keys(currentValues).length
              ? currentValues
              : null,
            extra_context: extraContext || null,
            data_source: LLM_METADATA_DATA_SOURCE_FINAL
          }
        }
      )

      if (currentRecord) {
        this.editor.updateRecordField(
          'title',
          generatedMetadata.title || currentRecord.title
        )
        this.editor.updateRecordField(
          'abstract',
          generatedMetadata.abstract || currentRecord.abstract
        )
        this.editor.updateRecordField(
          'keywords',
          generatedMetadata.keywords.map((kw: string) => ({
            label: kw,
            type: 'theme'
          }))
        )
        this.editor.updateRecordField(
          'topics',
          generatedMetadata.topic_categories || []
        )

        this.operationToastStore.addAISuccess(
          'info.operation.aiMetadataGeneration'
        )
      }
    } catch (error) {
      console.error('Error generating metadata with AI:', error)
      this.operationToastStore.addError('aiMetadataGeneration')
    } finally {
      this.isGeneratingAI.set(false)
    }
  }
}
