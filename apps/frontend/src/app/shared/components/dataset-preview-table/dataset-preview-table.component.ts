import { Component, input, computed, inject } from '@angular/core'
import { MatTableModule } from '@angular/material/table'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { DropdownChoice, SpinningLoaderComponent } from 'geonetwork-ui'
import { provideIcons, provideNgIconsConfig } from '@ng-icons/core'
import { iconoirDataTransferBoth } from '@ng-icons/iconoir'

@Component({
  selector: 'app-dataset-preview-table',
  imports: [MatTableModule, TranslatePipe, SpinningLoaderComponent],
  templateUrl: './dataset-preview-table.component.html',
  styleUrls: ['./dataset-preview-table.component.scss'],
  providers: [
    provideIcons({
      iconoirDataTransferBoth
    }),
    provideNgIconsConfig({
      size: '2em'
    })
  ]
})
export class DatasetPreviewTableComponent {
  private translate = inject(TranslateService)

  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)
  previewError = input<string | null>(null)
  previewLoading = input<boolean>(false)

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  displayedColumns = computed(() => {
    const meta = this.metadata()
    return meta?.columns.map((col) => col.name) || []
  })

  dataSource = computed(() => {
    const data = this.preview()?.data || []
    return data
  })

  columns = computed<DropdownChoice[]>(() => {
    const meta = this.metadata()
    if (!meta?.columns) {
      return [{ value: '', label: '-' }]
    }
    return [
      { value: '', label: '-' },
      ...meta.columns.map((col) => ({
        value: col.name,
        label: col.name
      }))
    ]
  })
}
