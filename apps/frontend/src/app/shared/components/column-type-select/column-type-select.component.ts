import {
  Component,
  input,
  output,
  computed,
  ChangeDetectionStrategy
} from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

export type CastType = 'boolean' | 'numeric' | 'text' | 'date'

marker('import.columnAction.typeMenu.boolean')
marker('import.columnAction.typeMenu.numeric')
marker('import.columnAction.typeMenu.text')
marker('import.columnAction.typeMenu.date')

@Component({
  selector: 'app-column-type-select',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe],
  templateUrl: './column-type-select.component.html'
})
export class ColumnTypeSelectComponent {
  originalType = input<string | null | undefined>()
  castType = input<string | null | undefined>()

  typeSelect = output<CastType | null>()

  castTypes = computed<CastType[]>(() => {
    const base: CastType[] = ['boolean', 'numeric', 'text']
    return this.originalType() === 'date' ? [...base, 'date'] : base
  })

  effectiveType = computed<string>(
    () => this.castType() ?? this.originalType() ?? 'text'
  )

  onTypeClick(type: CastType, event: MouseEvent): void {
    event.stopPropagation()
    if (type === this.castType() || type === this.originalType()) {
      this.typeSelect.emit(null)
    } else {
      this.typeSelect.emit(type)
    }
  }
}
