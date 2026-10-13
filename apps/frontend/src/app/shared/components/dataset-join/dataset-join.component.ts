import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
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
import { TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  DropdownChoice,
  DropdownSelectorComponent
} from 'geonetwork-ui'
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
export class DatasetJoinComponent {
  join = input<JoinConfig | null>(null)
  tables = input<JoinableTable[]>([])
  sourceColumns = input<ColumnConfig[]>([])
  targetColumns = input<string[]>([])

  tableChange = output<JoinableTable>()
  sourceColumnChange = output<string>()
  targetColumnChange = output<string>()
  columnAdd = output<string>()
  columnRemove = output<string>()

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

  tableLabel(table: JoinableTable): string {
    return table.integrity_title || table.table_name
  }

  selectTable(table: JoinableTable): void {
    this.tableListOpen.set(false)
    if (table !== this.selectedTable()) this.tableChange.emit(table)
  }

  addColumn(column: string): void {
    if (!column) return
    this.columnAdd.emit(column)
    // The dropdown keeps its own selection, which would show this column again
    // once it is removed and offered back.
    this.addDropdown()!.selected = ''
  }
}
