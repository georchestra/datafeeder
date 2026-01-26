import {
  Component,
  input,
  signal,
  effect,
  inject,
  computed,
  output
} from '@angular/core'
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { MatTableModule } from '@angular/material/table'
import { Api } from '../../../core/api/api'
import {
  getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
  getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet
} from '../../../core/api/functions'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'

@Component({
  selector: 'app-dataset-configuration',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    TranslatePipe
  ],
  templateUrl: './dataset-configuration.component.html',
  styleUrls: ['./dataset-configuration.component.scss']
})
export class DatasetConfigurationComponent {
  private api = inject(Api)
  private fb = inject(FormBuilder)
  private translate = inject(TranslateService)

  validated = output<string>()

  form = this.fb.group({
    title: this.fb.control('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(100)
      ]
    })
  })

  integrityLinkId = input<string | undefined>()
  metadata = signal<StagingMetadataResponse | null>(null)
  preview = signal<StagingPreviewResponse | null>(null)

  displayedColumns = computed(() => {
    const meta = this.metadata()
    return meta?.columns.map((col) => col.name) || []
  })

  dataSource = computed(() => {
    const data = this.preview()?.data || []
    return data
  })

  constructor() {
    effect(() => {
      const linkId = this.integrityLinkId()
      if (!linkId) return

      this.fetchData(linkId)
    })

    // Sync metadata title to form when loaded
    effect(() => {
      const meta = this.metadata()
      if (meta) {
        const title =
          meta.title ||
          this.translate.instant('import.datasetConfiguration.untitled')
        this.form.patchValue({ title }, { emitEvent: false })
      }
    })
  }

  private async fetchData(integrityLinkId: string): Promise<void> {
    try {
      const [metadata, preview] = await Promise.all([
        this.api.invoke(
          getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
          {
            integrity_link_id: integrityLinkId
          }
        ),
        this.api.invoke(
          getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet,
          {
            integrity_link_id: integrityLinkId,
            limit: 10
          }
        )
      ])

      this.metadata.set(metadata)
      this.preview.set(preview)
    } catch (error) {
      console.error('Error fetching staging data:', error)
    }
  }

  submitForm() {
    if (this.form.valid) {
      this.validated.emit(this.form.value.title!)
    } else {
      this.form.markAllAsTouched()
    }
  }
}
