import { HttpErrorResponse } from '@angular/common/http'
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  OnInit,
  output,
  signal,
  viewChild
} from '@angular/core'
import { OverlayModule } from '@angular/cdk/overlay'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirCheckCircle,
  iconoirNavArrowDown,
  iconoirNavArrowUp,
  iconoirTrash
} from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import {
  ButtonComponent,
  DropdownChoice,
  DropdownSelectorComponent
} from 'geonetwork-ui'
import { Api } from '../../../core/api/api'
import {
  getJoinableColumnsIngestionIntegrityLinksIntegrityLinkIdJoinableColumnsGet,
  listJoinableTablesIngestionIntegrityLinksJoinableTablesGet
} from '../../../core/api/functions'
import type {
  ColumnConfig,
  JoinableTable,
  JoinConfig
} from '../../../core/api/models'

const NONE: DropdownChoice = { value: '', label: '-' }
// Reserved output column of the transformation, a joined one would clash with it.
const ID_COLUMN = 'id_datafeeder'

@Component({
  selector: 'app-dataset-join',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    OverlayModule,
    NgIconComponent,
    TranslatePipe,
    ButtonComponent,
    DropdownSelectorComponent
  ],
  templateUrl: './dataset-join.component.html',
  providers: [
    provideIcons({
      iconoirCheckCircle,
      iconoirNavArrowDown,
      iconoirNavArrowUp,
      iconoirTrash
    })
  ]
})
export class DatasetJoinComponent implements OnInit {
  private api = inject(Api)
  private translate = inject(TranslateService)

  join = input<JoinConfig | null>(null)
  sourceColumns = input<ColumnConfig[]>([])

  joinChange = output<JoinConfig>()
  loadError = output<string>()

  tables = signal<JoinableTable[]>([])
  targetColumns = signal<string[]>([])
  tableListOpen = signal(false)
  private readonly addDropdown =
    viewChild<DropdownSelectorComponent>('addDropdown')

  selectedTable = computed(() => {
    const join = this.join()
    if (!join) return null
    return this.tables().find((t) => t.id === join.integrity_link_id) ?? null
  })

  sourceChoices = computed<DropdownChoice[]>(() => [
    NONE,
    ...this.sourceColumns().map((col) => ({
      value: col.original_name,
      label: col.new_name ?? col.original_name
    }))
  ])

  targetChoices = computed<DropdownChoice[]>(() => [
    NONE,
    ...this.targetColumns().map((col) => ({ value: col, label: col }))
  ])

  keysSelected = computed(
    () => !!this.join()?.source_column && !!this.join()?.target_column
  )

  availableColumns = computed<DropdownChoice[]>(() => {
    const added = this.join()?.columns ?? []
    return this.targetColumns()
      .filter((col) => col !== ID_COLUMN && !added.includes(col))
      .map((col) => ({ value: col, label: col }))
  })

  addChoices = computed<DropdownChoice[]>(() => [
    NONE,
    ...this.availableColumns()
  ])

  async ngOnInit(): Promise<void> {
    try {
      this.tables.set(
        await this.api.invoke(
          listJoinableTablesIngestionIntegrityLinksJoinableTablesGet,
          {}
        )
      )
    } catch (error) {
      this.showLoadError(error)
      return
    }
    const id = this.join()?.integrity_link_id
    if (id) await this.loadTargetColumns(id)
  }

  tableLabel(table: JoinableTable): string {
    return table.integrity_title || table.table_name
  }

  async selectTable(table: JoinableTable): Promise<void> {
    this.tableListOpen.set(false)
    if (table === this.selectedTable()) return
    this.joinChange.emit({
      integrity_link_id: table.id,
      source_column: this.join()?.source_column ?? '',
      target_column: '',
      columns: []
    })
    this.targetColumns.set([])
    await this.loadTargetColumns(table.id)
  }

  update(changes: Partial<JoinConfig>): void {
    this.joinChange.emit({ ...this.join()!, ...changes })
  }

  addColumn(column: string): void {
    if (!column) return
    this.update({ columns: [...(this.join()?.columns ?? []), column] })
    // The dropdown keeps its own selection, which would show this column again
    // once it is removed and offered back.
    this.addDropdown()!.selected = ''
  }

  removeColumn(column: string): void {
    this.update({
      columns: (this.join()?.columns ?? []).filter((col) => col !== column)
    })
  }

  private async loadTargetColumns(integrityLinkId: string): Promise<void> {
    try {
      const columns = await this.api.invoke(
        getJoinableColumnsIngestionIntegrityLinksIntegrityLinkIdJoinableColumnsGet,
        { integrity_link_id: integrityLinkId }
      )
      this.targetColumns.set(columns.map((col) => col.column_name))
    } catch (error) {
      this.showLoadError(error)
    }
  }

  private showLoadError(error: unknown): void {
    this.loadError.emit(
      error instanceof HttpErrorResponse && error.error?.detail
        ? error.error.detail
        : this.translate.instant('import.dataSource.genericError')
    )
  }
}
