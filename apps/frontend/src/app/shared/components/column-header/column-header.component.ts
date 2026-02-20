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
import { NgStyle } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { TranslateService } from '@ngx-translate/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnConfigOutput } from '../../../core/api/models'
import type { ColumnAction, CastType } from '../column-action-menu/column-action-menu.component'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import { ColumnActionMenuComponent } from '../column-action-menu/column-action-menu.component'

marker('import.columnHeader.error.empty')
marker('import.columnHeader.error.duplicate')

@Component({
  selector: 'app-column-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ColumnActionMenuComponent, FormsModule, NgStyle],
  templateUrl: './column-header.component.html'
})
export class ColumnHeaderComponent {
  private readonly elementRef = inject(ElementRef)
  private readonly translate = inject(TranslateService)

  columnConfig = input.required<ColumnConfigOutput>()
  /** All current display names (new_name ?? original_name) for duplicate detection. */
  allColumnNames = input<string[]>([])

  actionMenuOpened = output<ColumnAction>()
  /** Emits the validated new name when the user renames the column. */
  nameChanged = output<string>()
  /** Emits the selected cast type (or null to clear) when the user changes the type. */
  typeSelected = output<CastType | null>()
  /** Emits a validated filter (or null to delete) from the filter form. */
  filterChanged = output<ColumnFilter | null>()

  isMenuOpen = signal(false)
  nameValidationError = signal<string | null>(null)
  /** Position for the fixed-positioned dropdown menu. */
  menuStyle = signal<{ top: string; right: string } | null>(null)

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

  @HostListener('document:wheel')
  @HostListener('document:touchmove')
  onScrollEvent(): void {
    if (this.isMenuOpen()) {
      this.isMenuOpen.set(false)
    }
  }

  toggleMenu(event: MouseEvent): void {
    event.stopPropagation()
    const btn = event.currentTarget as HTMLElement
    const rect = btn.getBoundingClientRect()
    this.menuStyle.set({
      top: `${rect.bottom + 2}px`,
      right: `${window.innerWidth - rect.right}px`
    })
    this.isMenuOpen.update((open) => !open)
  }

  onMenuAction(action: ColumnAction): void {
    this.isMenuOpen.set(false)
    this.actionMenuOpened.emit(action)
  }

  onTypeSelected(type: CastType | null): void {
    this.isMenuOpen.set(false)
    this.typeSelected.emit(type)
  }

  onFilterValidated(filter: ColumnFilter): void {
    this.isMenuOpen.set(false)
    this.filterChanged.emit(filter)
  }

  onFilterDeleted(): void {
    this.isMenuOpen.set(false)
    this.filterChanged.emit(null)
  }

  onNameInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value.trim()
    const original = this.columnConfig().original_name

    if (!value) {
      this.nameValidationError.set(
        this.translate.instant('import.columnHeader.error.empty')
      )
      return
    }

    const otherNames = this.allColumnNames().filter(
      (n) => n !== (this.columnConfig().new_name ?? original)
    )
    if (otherNames.includes(value)) {
      this.nameValidationError.set(
        this.translate.instant('import.columnHeader.error.duplicate')
      )
      return
    }

    this.nameValidationError.set(null)
    this.nameChanged.emit(value)
  }
}
