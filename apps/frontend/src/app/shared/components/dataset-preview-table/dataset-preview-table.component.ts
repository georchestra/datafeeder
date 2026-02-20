import { Component, input, computed, inject, output, ChangeDetectionStrategy } from '@angular/core'
import { MatTableModule } from '@angular/material/table'
import type {
  ColumnConfigOutput,
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { SpinningLoaderComponent } from 'geonetwork-ui'
import { ColumnHeaderComponent } from '../column-header/column-header.component'
import type { ColumnAction } from '../column-action-menu/column-action-menu.component'

@Component({
  selector: 'app-dataset-preview-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatTableModule, TranslatePipe, SpinningLoaderComponent, ColumnHeaderComponent],
  templateUrl: './dataset-preview-table.component.html',
  styleUrls: ['./dataset-preview-table.component.scss']
})
export class DatasetPreviewTableComponent {
  private readonly translate = inject(TranslateService)

  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)
  previewError = input<string | null>(null)
  previewLoading = input<boolean>(false)

  columnActionRequested = output<{ originalName: string; action: ColumnAction }>()

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  /** Non-excluded columns, using new_name ?? original_name as the MatTable column key. */
  displayedColumns = computed(() => {
    const meta = this.metadata()
    return (meta?.columns ?? [])
      .filter((col) => !col.excluded)
      .map((col) => col.new_name ?? col.original_name)
  })

  dataSource = computed(() => this.preview()?.data ?? [])

  /** Look up a ColumnConfigOutput by its display name (new_name ?? original_name). */
  getColumnConfig(displayName: string): ColumnConfigOutput | null {
    return (
      (this.metadata()?.columns ?? []).find(
        (col) => (col.new_name ?? col.original_name) === displayName
      ) ?? null
    )
  }

  onColumnAction(displayName: string, action: ColumnAction): void {
    const col = this.getColumnConfig(displayName)
    if (col) {
      this.columnActionRequested.emit({ originalName: col.original_name, action })
    }
  }
}
