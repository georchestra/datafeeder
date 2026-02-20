import {
  Component,
  input,
  output,
  signal,
  computed,
  ChangeDetectionStrategy
} from '@angular/core'
import { FormsModule } from '@angular/forms'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import type { FilterOperator } from '../../../core/api/models/filter-operator'
import { FILTER_OPERATOR } from '../../../core/api/models/filter-operator-array'

marker('import.columnFilter.operator.exactly')
marker('import.columnFilter.operator.contains')
marker('import.columnFilter.operator.starts_with')
marker('import.columnFilter.valuePlaceholder')
marker('import.columnFilter.validate')
marker('import.columnFilter.delete')

@Component({
  selector: 'app-column-filter-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, TranslatePipe],
  templateUrl: './column-filter-form.component.html'
})
export class ColumnFilterFormComponent {
  /** Currently active filter (null = no active filter). */
  activeFilter = input<ColumnFilter | null>(null)

  /** Emits a validated filter when the user clicks "Validate". */
  filterValidated = output<ColumnFilter>()

  /** Emits when the user deletes the active filter. */
  filterDeleted = output<void>()

  readonly operators: FilterOperator[] = FILTER_OPERATOR

  selectedOperator = signal<FilterOperator>('contains')
  filterValue = signal<string>('')

  /** True when editing mode (no active filter or user is editing). */
  isEditing = computed(() => this.activeFilter() == null)

  onValidate(event: MouseEvent): void {
    event.stopPropagation()
    const value = this.filterValue().trim()
    if (!value) return
    this.filterValidated.emit({ operator: this.selectedOperator(), value })
  }

  onDelete(event: MouseEvent): void {
    event.stopPropagation()
    this.filterDeleted.emit()
  }

  onEdit(event: MouseEvent): void {
    event.stopPropagation()
    const current = this.activeFilter()
    if (current) {
      this.selectedOperator.set(current.operator)
      this.filterValue.set(current.value)
    }
  }
}
