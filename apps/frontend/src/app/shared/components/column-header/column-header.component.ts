import {
  Component,
  ElementRef,
  input,
  output,
  signal,
  computed,
  ChangeDetectionStrategy,
  ViewContainerRef,
  TemplateRef,
  viewChild,
  inject,
  OnDestroy
} from '@angular/core'
import {
  FlexibleConnectedPositionStrategy,
  Overlay,
  OverlayModule,
  OverlayRef
} from '@angular/cdk/overlay'
import { TemplatePortal } from '@angular/cdk/portal'
import { filter } from 'rxjs'
import { FormsModule } from '@angular/forms'
import { TranslateService } from '@ngx-translate/core'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirMoreVert, iconoirUndo } from '@ng-icons/iconoir'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import type { ColumnConfigOutput } from '../../../core/api/models'
import type {
  ColumnAction,
  CastType
} from '../column-action-menu/column-action-menu.component'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import { ColumnActionMenuComponent } from '../column-action-menu/column-action-menu.component'

marker('import.columnHeader.error.empty')
marker('import.columnHeader.error.duplicate')

@Component({
  selector: 'app-column-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ColumnActionMenuComponent,
    FormsModule,
    OverlayModule,
    NgIconComponent
  ],
  templateUrl: './column-header.component.html',
  providers: [
    provideIcons({ iconoirMoreVert, iconoirUndo }),
    provideNgIconsConfig({ size: '1.25rem' })
  ]
})
export class ColumnHeaderComponent implements OnDestroy {
  private readonly overlay = inject(Overlay)
  private readonly vcr = inject(ViewContainerRef)
  private readonly translate = inject(TranslateService)

  columnConfig = input.required<ColumnConfigOutput>()
  allColumnNames = input<string[]>([])

  actionMenuOpened = output<ColumnAction>()
  nameChanged = output<string>()
  nameValidationErrorChanged = output<string | null>()
  typeSelected = output<CastType | null>()
  filterChanged = output<ColumnFilter | null>()

  readonly triggerRef = viewChild<ElementRef<HTMLElement>>('triggerBtn')
  readonly menuTemplate = viewChild<TemplateRef<void>>('menuTemplate')

  private overlayRef: OverlayRef | null = null
  private positionStrategy: FlexibleConnectedPositionStrategy | null = null

  isMenuOpen = signal(false)
  nameValidationError = signal<string | null>(null)

  displayName = computed(
    () => this.columnConfig().new_name ?? this.columnConfig().original_name
  )

  hasActiveActions = computed(() => {
    const col = this.columnConfig()
    const hasCastOverride =
      col.cast_type != null && col.cast_type !== col.original_type
    return col.filter != null || hasCastOverride
  })

  isExcluded = computed(() => this.columnConfig().excluded === true)

  ngOnDestroy(): void {
    this.overlayRef?.dispose()
    this.positionStrategy = null
  }

  toggleMenu(event: MouseEvent): void {
    event.stopPropagation()
    if (this.overlayRef?.hasAttached()) {
      this.closeMenu()
    } else {
      this.openMenu()
    }
  }

  private openMenu(): void {
    const trigger = this.triggerRef()
    const template = this.menuTemplate()
    if (!trigger || !template) return

    if (!this.overlayRef) {
      this.positionStrategy = this.overlay
        .position()
        .flexibleConnectedTo(trigger)
        .withPositions([
          {
            originX: 'end',
            originY: 'bottom',
            overlayX: 'end',
            overlayY: 'top',
            offsetY: 2
          },
          {
            originX: 'end',
            originY: 'top',
            overlayX: 'end',
            overlayY: 'bottom',
            offsetY: -2
          }
        ])
        .withPush(false)

      this.overlayRef = this.overlay.create({
        positionStrategy: this.positionStrategy,
        scrollStrategy: this.overlay.scrollStrategies.close(),
        hasBackdrop: false
      })

      this.overlayRef
        .outsidePointerEvents()
        .pipe(
          filter(
            (e) =>
              !this.triggerRef()?.nativeElement.contains(
                e.target as HTMLElement
              )
          )
        )
        .subscribe(() => this.closeMenu())
    } else {
      this.positionStrategy!.setOrigin(trigger)
    }

    this.overlayRef.attach(new TemplatePortal(template, this.vcr))
    this.isMenuOpen.set(true)
  }

  private closeMenu(): void {
    if (!this.overlayRef?.hasAttached()) return
    this.overlayRef.detach()
    this.isMenuOpen.set(false)
  }

  onMenuAction(action: ColumnAction): void {
    this.closeMenu()
    this.actionMenuOpened.emit(action)
  }

  onTypeSelected(type: CastType | null): void {
    this.closeMenu()
    this.typeSelected.emit(type)
  }

  onFilterValidated(filter: ColumnFilter): void {
    this.closeMenu()
    this.filterChanged.emit(filter)
  }

  onFilterDeleted(): void {
    this.closeMenu()
    this.filterChanged.emit(null)
  }

  onNameInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value.trim()
    const original = this.columnConfig().original_name

    if (!value) {
      const error = this.translate.instant('import.columnHeader.error.empty')
      this.nameValidationError.set(error)
      this.nameValidationErrorChanged.emit(error)
      return
    }

    const otherNames = this.allColumnNames().filter(
      (n) => n !== (this.columnConfig().new_name ?? original)
    )
    if (otherNames.includes(value)) {
      const error = this.translate.instant(
        'import.columnHeader.error.duplicate'
      )
      this.nameValidationError.set(error)
      this.nameValidationErrorChanged.emit(error)
      return
    }

    this.nameValidationError.set(null)
    this.nameValidationErrorChanged.emit(null)
    this.nameChanged.emit(value)
  }
}
