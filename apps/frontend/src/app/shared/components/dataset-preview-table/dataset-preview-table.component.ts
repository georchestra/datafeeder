import {
  Component,
  input,
  computed,
  inject,
  output,
  ChangeDetectionStrategy
} from '@angular/core'
import { MatTableModule } from '@angular/material/table'
import type {
  ColumnConfigOutput,
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { SpinningLoaderComponent } from 'geonetwork-ui'
import { ColumnHeaderComponent } from '../column-header/column-header.component'
import type {
  ColumnAction,
  CastType
} from '../column-action-menu/column-action-menu.component'
import type { ColumnFilter } from '../../../core/api/models/column-filter'

marker('import.datasetPreviewTable.allColumnsExcluded')

@Component({
  selector: 'app-dataset-preview-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MatTableModule,
    TranslatePipe,
    SpinningLoaderComponent,
    ColumnHeaderComponent
  ],
  templateUrl: './dataset-preview-table.component.html',
  styleUrls: ['./dataset-preview-table.component.scss']
})
export class DatasetPreviewTableComponent {
  private readonly translate = inject(TranslateService)

  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)
  previewError = input<string | null>(null)
  previewLoading = input<boolean>(false)

  columnActionRequested = output<{
    originalName: string
    action: ColumnAction
  }>()
  columnRenameRequested = output<{ originalName: string; newName: string }>()
  columnTypeChangeRequested = output<{
    originalName: string
    type: CastType | null
  }>()
  columnFilterChangeRequested = output<{
    originalName: string
    filter: ColumnFilter | null
  }>()

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  /** All display names (new_name ?? original_name) for ALL columns — used for duplicate detection. */
  allDisplayNames = computed(() =>
    (this.metadata()?.columns ?? []).map(
      (col) => col.new_name ?? col.original_name
    )
  )

  /** All column display names used as MatTable column keys (excluded columns still shown). */
  displayedColumns = computed(() => {
    const meta = this.metadata()
    return (meta?.columns ?? []).map((col) => col.new_name ?? col.original_name)
  })

  /** True when every column has excluded=true (edge case EC3). */
  allColumnsExcluded = computed(() => {
    const cols = this.metadata()?.columns ?? []
    return cols.length > 0 && cols.every((col) => col.excluded === true)
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

  isColumnExcluded(displayName: string): boolean {
    return this.getColumnConfig(displayName)?.excluded === true
  }

  onColumnAction(displayName: string, action: ColumnAction): void {
    const col = this.getColumnConfig(displayName)
    if (col) {
      this.columnActionRequested.emit({
        originalName: col.original_name,
        action
      })
    }
  }

  onColumnFilterChange(displayName: string, filter: ColumnFilter | null): void {
    const col = this.getColumnConfig(displayName)
    if (col) {
      this.columnFilterChangeRequested.emit({
        originalName: col.original_name,
        filter
      })
    }
  }

  onColumnTypeChange(displayName: string, type: CastType | null): void {
    const col = this.getColumnConfig(displayName)
    if (col) {
      this.columnTypeChangeRequested.emit({
        originalName: col.original_name,
        type
      })
    }
  }

  onColumnRename(displayName: string, newName: string): void {
    const col = this.getColumnConfig(displayName)
    if (col) {
      this.columnRenameRequested.emit({
        originalName: col.original_name,
        newName
      })
    }
  }
}
