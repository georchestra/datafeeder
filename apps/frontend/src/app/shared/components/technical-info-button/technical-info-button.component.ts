import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  OnDestroy,
  signal,
  TemplateRef,
  ViewContainerRef,
  viewChild
} from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import {
  FlexibleConnectedPositionStrategy,
  Overlay,
  OverlayModule,
  OverlayRef
} from '@angular/cdk/overlay'
import { TemplatePortal } from '@angular/cdk/portal'
import { filter, fromEvent } from 'rxjs'
import { TranslatePipe } from '@ngx-translate/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirHelpCircle } from '@ng-icons/iconoir'
import { UiAlertBoxComponent } from '../ui-alert-box/ui-alert-box.component'

@Component({
  selector: 'app-technical-info-button',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [OverlayModule, NgIconComponent, TranslatePipe, UiAlertBoxComponent],
  templateUrl: './technical-info-button.component.html',
  providers: [provideIcons({ iconoirHelpCircle })]
})
export class TechnicalInfoButtonComponent implements OnDestroy {
  private readonly overlay = inject(Overlay)
  private readonly vcr = inject(ViewContainerRef)
  private readonly destroyRef = inject(DestroyRef)

  readonly triggerRef = viewChild<ElementRef<HTMLElement>>('triggerBtn')
  readonly panelTemplate = viewChild<TemplateRef<void>>('panelTemplate')

  isOpen = signal(false)

  private overlayRef: OverlayRef | null = null
  private positionStrategy: FlexibleConnectedPositionStrategy | null = null

  ngOnDestroy(): void {
    this.overlayRef?.dispose()
    this.positionStrategy = null
  }

  openPanel(): void {
    const trigger = this.triggerRef()
    const template = this.panelTemplate()
    if (!trigger || !template) return

    if (!this.overlayRef) {
      this.positionStrategy = this.overlay
        .position()
        .flexibleConnectedTo(trigger)
        .withPositions([
          {
            originX: 'end',
            originY: 'top',
            overlayX: 'end',
            overlayY: 'top',
            offsetY: 4
          }
        ])
        .withPush(false)

      this.overlayRef = this.overlay.create({
        positionStrategy: this.positionStrategy,
        scrollStrategy: this.overlay.scrollStrategies.close(),
        hasBackdrop: false
      })

      fromEvent<MouseEvent>(document, 'pointerdown')
        .pipe(
          filter(() => this.overlayRef?.hasAttached() ?? false),
          filter((e) => {
            const target = e.target as HTMLElement
            return !(this.overlayRef?.overlayElement?.contains(target) ?? false)
          }),
          takeUntilDestroyed(this.destroyRef)
        )
        .subscribe(() => this.closePanel())
    } else {
      this.positionStrategy!.setOrigin(trigger)
    }

    this.overlayRef.attach(new TemplatePortal(template, this.vcr))
    this.isOpen.set(true)
  }

  closePanel(): void {
    if (!this.overlayRef?.hasAttached()) return
    this.overlayRef.detach()
    this.isOpen.set(false)
  }
}
