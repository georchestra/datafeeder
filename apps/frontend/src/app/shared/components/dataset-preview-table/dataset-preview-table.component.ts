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

  allDisplayNames = computed(() =>
    (this.metadata()?.columns ?? []).map(
      (col) => col.new_name ?? col.original_name
    )
  )

  displayedColumns = computed(() => {
    const meta = this.metadata()
    return (meta?.columns ?? []).map((col) => col.original_name)
  })

  allColumnsExcluded = computed(() => {
    const cols = this.metadata()?.columns ?? []
    return cols.length > 0 && cols.every((col) => col.excluded === true)
  })

  dataSource = computed(() => this.preview()?.data ?? [])

  onColumnAction(originalName: string, action: ColumnAction): void {
    this.columnActionRequested.emit({ originalName, action })
  }

  onColumnFilterChange(
    originalName: string,
    filter: ColumnFilter | null
  ): void {
    this.columnFilterChangeRequested.emit({ originalName, filter })
  }

  onColumnTypeChange(originalName: string, type: CastType | null): void {
    this.columnTypeChangeRequested.emit({ originalName, type })
  }

  onColumnRename(originalName: string, newName: string): void {
    this.columnRenameRequested.emit({ originalName, newName })
  }
}
