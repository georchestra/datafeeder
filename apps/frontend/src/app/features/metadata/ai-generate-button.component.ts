import { Component, computed, input, inject, signal } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirEditPencil,
  iconoirMagicWand,
  iconoirNavArrowDown,
  iconoirNavArrowLeft,
  iconoirSend,
  iconoirSparks
} from '@ng-icons/iconoir'
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

marker('footer.aiGeneratingMetadata')
marker('footer.ai.rewriteAndImprove')
marker('footer.ai.rewriteAndImprove.hint')
marker('footer.ai.regenerate')
marker('footer.ai.regenerate.hint')
marker('footer.ai.addYourPrompt')
marker('footer.ai.addYourPrompt.hint')
marker('footer.ai.promptPlaceholder')
marker('footer.ai.send')
marker('footer.ai.customPrompt.title')
marker('footer.ai.applyToFields')
marker('footer.ai.appliesToFields')
marker('footer.ai.deselectAll')
marker('footer.ai.selectAll')
marker('footer.ai.fieldsSelected')
marker('footer.ai.field.title')
marker('footer.ai.field.abstract')
marker('footer.ai.field.keywords')
marker('footer.ai.field.topics')
marker('footer.ai.field.dateExtents')
marker('footer.ai.field.attributeTables')
marker('metadata.ai.confirmOverwrite.title')
marker('metadata.ai.confirmOverwrite.message')
marker('metadata.ai.confirmOverwrite.confirm')
marker('metadata.ai.confirmOverwrite.cancel')
marker('errors.operation.aiMetadataGeneration')
marker('info.operation.aiMetadataGeneration')

const LLM_METADATA_DATA_SOURCE_FINAL: LlmMetadataDataSource = 'final'

type AiFieldKey =
  | 'title'
  | 'abstract'
  | 'keywords'
  | 'topics'
  | 'dateExtents'
  | 'attributeTables'

@Component({
  selector: 'app-ai-generate-button',
  imports: [NgIconComponent, TranslatePipe, FormsModule],
  templateUrl: './ai-generate-button.component.html',
  providers: [
    provideIcons({
      iconoirEditPencil,
      iconoirMagicWand,
      iconoirNavArrowDown,
      iconoirNavArrowLeft,
      iconoirSend,
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
  aiDropdownOpen = signal(false)
  aiDropdownView = signal<'prompt'>('prompt')
  aiCustomPrompt = signal('')
  disabled = input(false)
  lastAiMode = signal<'regenerate' | 'rewrite'>('regenerate')

  mainAiLabelKey = computed(() =>
    this.lastAiMode() === 'rewrite'
      ? 'footer.ai.rewriteAndImprove'
      : 'footer.ai.regenerate'
  )

  aiFields = signal<Record<AiFieldKey, boolean>>({
    title: true,
    abstract: true,
    keywords: true,
    topics: true,
    dateExtents: true,
    attributeTables: true
  })

  aiSelectedFieldsCount = computed(
    () => Object.values(this.aiFields()).filter(Boolean).length
  )

  aiSelectedFieldLabelKeys = computed(() =>
    (Object.keys(this.aiFields()) as AiFieldKey[])
      .filter((key) => this.aiFields()[key])
      .map((key) => `footer.ai.field.${key}`)
  )

  private changedSinceSave = toSignal(this.editor.changedSinceSave$, {
    initialValue: false
  })

  async onGenerateWithAI(
    mode: 'regenerate' | 'rewrite' = 'regenerate',
    extraContext?: string
  ): Promise<void> {
    this.aiDropdownOpen.set(false)
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
      const fields = this.aiFields()
      const currentRecord: CatalogRecord | null = (await firstValueFrom(
        this.editor.record$
      )) as CatalogRecord | null

      // Send ALL current values as context for the LLM (regardless of checkbox state).
      // The checkboxes only control which fields get updated in the form afterwards.
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
        if (fields.title)
          this.editor.updateRecordField(
            'title',
            generatedMetadata.title || currentRecord.title
          )
        if (fields.abstract)
          this.editor.updateRecordField(
            'abstract',
            generatedMetadata.abstract || currentRecord.abstract
          )
        if (fields.keywords)
          this.editor.updateRecordField(
            'keywords',
            generatedMetadata.keywords.map((kw) => ({
              label: kw,
              type: 'theme'
            }))
          )
        if (fields.topics)
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

  toggleAiField(field: AiFieldKey): void {
    this.aiFields.update((f) => ({ ...f, [field]: !f[field] }))
  }

  toggleAllAiFields(): void {
    const allSelected = this.aiSelectedFieldsCount() === 6
    this.aiFields.update(
      (f) =>
        Object.fromEntries(
          Object.keys(f).map((k) => [k, !allSelected])
        ) as Record<AiFieldKey, boolean>
    )
  }

  async onSendCustomPrompt(): Promise<void> {
    const prompt = this.aiCustomPrompt().trim()
    if (!prompt) return
    this.aiDropdownView.set('prompt')
    await this.onGenerateWithAI('regenerate', prompt)
    this.aiCustomPrompt.set('')
  }

  toggleAiDropdown(): void {
    if (!this.aiDropdownOpen()) {
      this.aiDropdownView.set('prompt')
    }
    this.aiDropdownOpen.update((v) => !v)
  }
}
