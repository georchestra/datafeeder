import {
  Component,
  input,
  output,
  signal,
  computed,
  ChangeDetectionStrategy,
  HostListener,
  ElementRef,
  inject
} from '@angular/core'
import type { ColumnConfigOutput } from '../../../core/api/models'
import type { ColumnAction } from '../column-action-menu/column-action-menu.component'
import { ColumnActionMenuComponent } from '../column-action-menu/column-action-menu.component'

@Component({
  selector: 'app-column-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ColumnActionMenuComponent],
  templateUrl: './column-header.component.html'
})
export class ColumnHeaderComponent {
  private readonly elementRef = inject(ElementRef)

  columnConfig = input.required<ColumnConfigOutput>()

  actionMenuOpened = output<ColumnAction>()

  isMenuOpen = signal(false)

  displayName = computed(
    () => this.columnConfig().new_name ?? this.columnConfig().original_name
  )

  hasActiveActions = computed(
    () =>
      this.columnConfig().filter != null || this.columnConfig().cast_type != null
  )

  isExcluded = computed(() => this.columnConfig().excluded === true)

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isMenuOpen.set(false)
    }
  }

  toggleMenu(event: MouseEvent): void {
    event.stopPropagation()
    this.isMenuOpen.update((open) => !open)
  }

  onMenuAction(action: ColumnAction): void {
    this.isMenuOpen.set(false)
    this.actionMenuOpened.emit(action)
  }
}
