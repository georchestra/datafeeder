import {
  CdkConnectedOverlay,
  CdkOverlayOrigin,
  ConnectedPosition,
  OverlayModule
} from '@angular/cdk/overlay'
import {
  Component,
  ElementRef,
  Input,
  QueryList,
  ViewChild,
  ViewChildren,
  input,
  model
} from '@angular/core'
import { firstValueFrom } from 'rxjs'
import { ButtonComponent } from 'geonetwork-ui'
import { TranslatePipe } from '@ngx-translate/core'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { matExpandLess, matExpandMore } from '@ng-icons/material-icons/baseline'

export interface MultiSelectChoice {
  id: string
  label: string
}

const DEFAULT_ROW_NUMBERS = 6

@Component({
  selector: 'app-multi-select-dropdown',
  templateUrl: './multi-select-dropdown.component.html',
  imports: [ButtonComponent, OverlayModule, TranslatePipe, NgIconComponent],
  providers: [
    provideIcons({ matExpandLess, matExpandMore }),
    provideNgIconsConfig({ size: '1.5em' })
  ]
})
export class MultiSelectDropdownComponent {
  label = input.required<string>()
  choices = input.required<MultiSelectChoice[]>()
  selected = model<string[]>([])

  @Input() maxRows: number = DEFAULT_ROW_NUMBERS

  @ViewChild('overlayOrigin') overlayOrigin!: CdkOverlayOrigin
  @ViewChild(CdkConnectedOverlay) overlay!: CdkConnectedOverlay
  overlayOpen = false
  overlayWidth = 'auto'
  overlayMaxHeight = 'none'
  overlayPositions: ConnectedPosition[] = [
    {
      originX: 'start',
      originY: 'bottom',
      overlayX: 'start',
      overlayY: 'top',
      offsetY: 8
    },
    {
      originX: 'start',
      originY: 'top',
      overlayX: 'start',
      overlayY: 'bottom',
      offsetY: -8
    }
  ]

  @ViewChildren('choiceInputs', { read: ElementRef })
  choiceInputs!: QueryList<ElementRef>

  isSelected(choice: MultiSelectChoice): boolean {
    return this.selected().includes(choice.id)
  }

  toggleChoice(choice: MultiSelectChoice): void {
    this.selected.update((ids) =>
      ids.includes(choice.id)
        ? ids.filter((id) => id !== choice.id)
        : [...ids, choice.id]
    )
  }

  openOverlay() {
    this.overlayWidth =
      this.overlayOrigin.elementRef.nativeElement.getBoundingClientRect()
        .width + 'px'
    this.overlayMaxHeight = this.maxRows
      ? `${this.maxRows * 29 + 60}px`
      : 'none'
    this.overlayOpen = true
    // QueryList.changes never emits when the list stays empty
    return Promise.all([
      firstValueFrom(this.overlay.attach),
      this.choices().length ? firstValueFrom(this.choiceInputs.changes) : null
    ])
  }

  closeOverlay() {
    this.overlayOpen = false
  }

  focusFirstItem() {
    this.choiceInputs.get(0)?.nativeElement.focus()
  }

  focusLastItem() {
    this.choiceInputs.get(this.choiceInputs.length - 1)?.nativeElement.focus()
  }

  async handleTriggerKeydown(event: KeyboardEvent) {
    const keyCode = event.code
    const isOpenKey =
      keyCode === 'ArrowDown' ||
      keyCode === 'ArrowUp' ||
      keyCode === 'ArrowLeft' ||
      keyCode === 'ArrowRight' ||
      keyCode === 'Enter' ||
      keyCode === 'Space'
    const isCloseKey = keyCode === 'Escape'
    if (isOpenKey) {
      event.preventDefault()
      if (!this.overlayOpen) {
        await this.openOverlay()
      }
      if (keyCode === 'ArrowLeft' || keyCode === 'ArrowUp') this.focusLastItem()
      else this.focusFirstItem()
    } else if (this.overlayOpen && isCloseKey) {
      event.preventDefault()
      this.closeOverlay()
    }
  }

  handleOverlayKeydown(event: KeyboardEvent) {
    if (!this.overlayOpen) return
    const keyCode = event.code
    if (keyCode === 'ArrowDown' || keyCode === 'ArrowRight') {
      event.preventDefault()
      this.shiftItemFocus(1)
    } else if (keyCode === 'ArrowLeft' || keyCode === 'ArrowUp') {
      event.preventDefault()
      this.shiftItemFocus(-1)
    } else if (keyCode === 'Escape') {
      this.closeOverlay()
    }
  }

  shiftItemFocus(shift: number) {
    const index = this.focusedIndex
    if (index === -1) return
    const max = this.choiceInputs.length
    const newIndex = (((index + shift) % max) + max) % max
    this.choiceInputs.get(newIndex)?.nativeElement.focus()
  }

  get focusedIndex(): number | -1 {
    return this.choiceInputs.reduce(
      (prev, curr, curIndex) =>
        curr.nativeElement === document.activeElement ? curIndex : prev,
      -1
    )
  }

  toggleIfEnter(event: KeyboardEvent, choice: MultiSelectChoice) {
    if (event.code === 'Enter' || event.code === 'Space') {
      event.preventDefault()
      this.toggleChoice(choice)
    }
  }
}
