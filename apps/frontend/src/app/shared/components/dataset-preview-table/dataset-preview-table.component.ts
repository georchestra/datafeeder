import {
  Component,
  input,
  computed,
  inject,
  output,
  ChangeDetectionStrategy,
  ElementRef,
  Injector,
  afterNextRender,
  viewChild
} from '@angular/core'
import { MatTableModule } from '@angular/material/table'
import type {
  JoinedColumn,
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

// Prefixed so a joined column never shares its column definition ID, or its
// name error key, with a source column of the same name.
export function joinColumnId(originalName: string): string {
  return `join:${originalName}`
}

// Mirrors the backend: a geometry column is never renamed.
export function outputName(col: {
  original_name: string
  new_name?: string | null
}): string {
  return col.original_name === 'geom'
    ? 'geom'
    : col.new_name ?? col.original_name
}

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
  private readonly injector = inject(Injector)

  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)
  previewError = input<string | null>(null)
  previewLoading = input<boolean>(false)
  joinColumns = input<JoinedColumn[]>([])
  joinClashes = input<string[]>([])

  private readonly scrollContainer =
    viewChild<ElementRef<HTMLElement>>('scrollContainer')

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
  columnNameValidationErrorChanged = output<{
    originalName: string
    error: string | null
  }>()
  joinColumnRenameRequested = output<{
    originalName: string
    newName: string
  }>()
  joinColumnFilterChangeRequested = output<{
    originalName: string
    filter: ColumnFilter | null
  }>()

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  allDisplayNames = computed(() => [
    ...(this.metadata()?.columns ?? []).map(
      (col) => col.new_name ?? col.original_name
    ),
    ...this.joinColumns().map(outputName)
  ])

  // Excluded source columns free their name for a joined column.
  joinHeaderNames = computed(() => [
    ...(this.metadata()?.columns ?? [])
      .filter((col) => !col.excluded)
      .map(outputName),
    ...this.joinColumns().map(outputName)
  ])

  // Material table tracks column definitions by a string ID. We use original_name
  // as that ID (not new_name) so the definition stays stable even when the user
  // renames a column mid-session. The display label is rendered separately inside
  // the column header component using the effective name (new_name ?? original_name).
  displayedColumns = computed(() => {
    const meta = this.metadata()
    return [
      ...(meta?.columns ?? []).map((col) => col.original_name),
      ...this.joinColumns().map((col) => joinColumnId(col.original_name))
    ]
  })

  allColumnsExcluded = computed(() => {
    const cols = this.metadata()?.columns ?? []
    return cols.length > 0 && cols.every((col) => col.excluded === true)
  })

  dataSource = computed(() => this.preview()?.data ?? [])

  scrollToEnd(): void {
    afterNextRender(
      () => {
        const el = this.scrollContainer()?.nativeElement
        if (el) el.scrollLeft = el.scrollWidth
      },
      { injector: this.injector }
    )
  }

  joinColumnId = joinColumnId
  outputName = outputName

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

  onJoinColumnRename(originalName: string, newName: string): void {
    this.joinColumnRenameRequested.emit({ originalName, newName })
  }

  onJoinColumnFilterChange(
    originalName: string,
    filter: ColumnFilter | null
  ): void {
    this.joinColumnFilterChangeRequested.emit({ originalName, filter })
  }

  onColumnNameValidationErrorChange(
    originalName: string,
    error: string | null
  ): void {
    this.columnNameValidationErrorChanged.emit({ originalName, error })
  }
}
