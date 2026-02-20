import {
  Component,
  input,
  output,
  computed,
  ChangeDetectionStrategy
} from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnConfigOutput } from '../../../core/api/models'

export type ColumnAction = 'filter' | 'changeType' | 'remove'

marker('import.columnAction.menu.filter')
marker('import.columnAction.menu.changeType')
marker('import.columnAction.menu.remove')

@Component({
  selector: 'app-column-action-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe],
  templateUrl: './column-action-menu.component.html'
})
export class ColumnActionMenuComponent {
  columnConfig = input.required<ColumnConfigOutput>()

  actionSelected = output<ColumnAction>()

  hasFilterActive = computed(() => this.columnConfig().filter != null)
  hasCastTypeActive = computed(() => this.columnConfig().cast_type != null)

  onAction(action: ColumnAction, event: MouseEvent): void {
    event.stopPropagation()
    this.actionSelected.emit(action)
  }
}
