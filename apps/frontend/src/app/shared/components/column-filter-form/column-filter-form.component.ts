import {
  Component,
  input,
  output,
  signal,
  ChangeDetectionStrategy
} from '@angular/core'
import { FormsModule } from '@angular/forms'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirSearch,
  iconoirTrash,
  iconoirTransitionUp
} from '@ng-icons/iconoir'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import type { FilterOperator } from '../../../core/api/models/filter-operator'

marker('import.columnFilter.operator.exactly')
marker('import.columnFilter.operator.contains')
marker('import.columnFilter.operator.starts_with')
marker('import.columnFilter.placeholder.contains')
marker('import.columnFilter.placeholder.exactly')
marker('import.columnFilter.placeholder.starts_with')
marker('import.columnFilter.delete')

@Component({
  selector: 'app-column-filter-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, TranslatePipe, NgIconComponent],
  viewProviders: [
    provideIcons({ iconoirSearch, iconoirTrash, iconoirTransitionUp })
  ],
  templateUrl: './column-filter-form.component.html'
})
export class ColumnFilterFormComponent {
  /** Currently active filter (null = no active filter). */
  activeFilter = input<ColumnFilter | null>(null)

  /** Emits a validated filter when the user submits any input. */
  filterValidated = output<ColumnFilter>()

  /** Emits when the user deletes the active filter. */
  filterDeleted = output<void>()

  containsValue = signal<string>('')
  exactlyValue = signal<string>('')
  startsWithValue = signal<string>('')

  onSubmit(operator: FilterOperator, value: string): void {
    const trimmed = value.trim()
    if (!trimmed) return
    this.filterValidated.emit({ operator, value: trimmed })
    this.containsValue.set('')
    this.exactlyValue.set('')
    this.startsWithValue.set('')
  }

  onDelete(event: MouseEvent): void {
    event.stopPropagation()
    this.filterDeleted.emit()
  }
}
