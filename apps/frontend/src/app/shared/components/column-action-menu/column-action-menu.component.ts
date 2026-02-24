import {
  Component,
  input,
  output,
  computed,
  signal,
  ChangeDetectionStrategy
} from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnConfigOutput } from '../../../core/api/models'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import { ColumnFilterFormComponent } from '../column-filter-form/column-filter-form.component'

export type ColumnAction = 'filter' | 'changeType' | 'remove'
export type CastType = 'boolean' | 'numeric' | 'text' | 'date'

marker('import.columnAction.menu.filter')
marker('import.columnAction.menu.changeType')
marker('import.columnAction.menu.remove')
marker('import.columnAction.typeMenu.boolean')
marker('import.columnAction.typeMenu.numeric')
marker('import.columnAction.typeMenu.text')
marker('import.columnAction.typeMenu.date')

@Component({
  selector: 'app-column-action-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe, ColumnFilterFormComponent],
  templateUrl: './column-action-menu.component.html'
})
export class ColumnActionMenuComponent {
  columnConfig = input.required<ColumnConfigOutput>()

  actionSelected = output<ColumnAction>()
  /** Emits the selected cast type, or null to deselect (clear cast_type). */
  typeSelected = output<CastType | null>()
  /** Emits a validated filter from the inline filter form. */
  filterValidated = output<ColumnFilter>()
  /** Emits when the active filter is deleted. */
  filterDeleted = output<void>()

  hasFilterActive = computed(() => this.columnConfig().filter != null)
  hasCastTypeActive = computed(() => {
    const castType = this.columnConfig().cast_type
    const originalType = this.columnConfig().original_type
    return castType != null && castType !== originalType
  })
  effectiveType = computed(
    () =>
      this.columnConfig().cast_type ??
      this.columnConfig().original_type ??
      'text'
  )

  typeExpanded = signal(false)
  filterExpanded = signal(false)

  castTypes = computed<CastType[]>(() => {
    const base: CastType[] = ['boolean', 'numeric', 'text']
    return this.columnConfig().original_type === 'date'
      ? [...base, 'date']
      : base
  })

  onAction(action: ColumnAction, event: MouseEvent): void {
    event.stopPropagation()
    if (action === 'changeType') {
      this.filterExpanded.set(false)
      this.typeExpanded.update((v) => !v)
    } else if (action === 'filter') {
      this.typeExpanded.set(false)
      this.filterExpanded.update((v) => !v)
    } else {
      this.typeExpanded.set(false)
      this.filterExpanded.set(false)
      this.actionSelected.emit(action)
    }
  }

  onTypeSelect(type: CastType, event: MouseEvent): void {
    event.stopPropagation()
    const castType = this.columnConfig().cast_type
    const originalType = this.columnConfig().original_type
    if (type === castType || type === originalType) {
      this.typeSelected.emit(null)
    } else {
      this.typeSelected.emit(type)
    }
  }

  onFilterValidated(filter: ColumnFilter): void {
    this.filterExpanded.set(false)
    this.filterValidated.emit(filter)
  }

  onFilterDeleted(): void {
    this.filterExpanded.set(false)
    this.filterDeleted.emit()
  }
}
