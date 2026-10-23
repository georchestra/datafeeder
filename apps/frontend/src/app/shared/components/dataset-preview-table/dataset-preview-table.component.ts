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
marker('import.columnHeader.error.duplicate')

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
  joinColumns = input<string[]>([])
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

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  // Clashing joined columns whose name is taken by a source column: the error
  // is shown on that column, the only one that can be renamed. The others clash
  // with the point built from X/Y and keep the error on the joined column.
  sourceClashes = computed(() => {
    const names = (this.metadata()?.columns ?? [])
      .filter((col) => !col.excluded)
      .map((col) => col.new_name ?? col.original_name)
    return this.joinClashes().filter((name) => names.includes(name))
  })

  allDisplayNames = computed(() => [
    ...(this.metadata()?.columns ?? []).map(
      (col) => col.new_name ?? col.original_name
    ),
    ...this.joinColumns()
  ])

  // Material table tracks column definitions by a string ID. We use original_name
  // as that ID (not new_name) so the definition stays stable even when the user
  // renames a column mid-session. The display label is rendered separately inside
  // the column header component using the effective name (new_name ?? original_name).
  displayedColumns = computed(() => {
    const meta = this.metadata()
    return [
      ...(meta?.columns ?? []).map((col) => col.original_name),
      ...this.joinColumns().map((name) => this.joinColumnId(name))
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

  // Prefixed so a joined column never shares its column definition ID with a
  // source column of the same name.
  joinColumnId(name: string): string {
    return `join:${name}`
  }

  joinOnlyClash(name: string): boolean {
    return (
      this.joinClashes().includes(name) && !this.sourceClashes().includes(name)
    )
  }

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

  onColumnNameValidationErrorChange(
    originalName: string,
    error: string | null
  ): void {
    this.columnNameValidationErrorChanged.emit({ originalName, error })
  }
}
