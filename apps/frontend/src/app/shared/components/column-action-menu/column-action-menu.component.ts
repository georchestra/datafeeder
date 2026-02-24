import {
  Component,
  input,
  output,
  computed,
  signal,
  ChangeDetectionStrategy
} from '@angular/core'
import { NgIconComponent, provideIcons, provideNgIconsConfig } from '@ng-icons/core'
import { iconoirTrash, iconoirNavArrowDown, iconoirNavArrowUp } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnConfigOutput } from '../../../core/api/models'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import { ColumnFilterFormComponent } from '../column-filter-form/column-filter-form.component'
import { ColumnTypeSelectComponent } from '../column-type-select/column-type-select.component'
import type { CastType } from '../column-type-select/column-type-select.component'

export type { CastType }
export type ColumnAction = 'filter' | 'changeType' | 'remove'

marker('import.columnAction.menu.filter')
marker('import.columnAction.menu.changeType')
marker('import.columnAction.menu.remove')

@Component({
  selector: 'app-column-action-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe, ColumnFilterFormComponent, ColumnTypeSelectComponent, NgIconComponent],
  templateUrl: './column-action-menu.component.html',
  providers: [provideIcons({ iconoirTrash, iconoirNavArrowDown, iconoirNavArrowUp }), provideNgIconsConfig({ size: '1.5rem' })]
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
  typeExpanded = signal(false)
  filterExpanded = signal(false)

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

  onTypeSelect(type: CastType | null): void {
    this.typeSelected.emit(type)
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
