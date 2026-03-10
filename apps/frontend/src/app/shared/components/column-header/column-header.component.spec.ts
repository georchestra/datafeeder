import { TestBed } from '@angular/core/testing'
import { Subject } from 'rxjs'
import { Overlay, OverlayRef } from '@angular/cdk/overlay'
import { ColumnHeaderComponent } from './column-header.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { ColumnConfigOutput } from '../../../core/api/models'

const translations = {
  'import.columnAction.menu.filter': 'Filtrer la colonne',
  'import.columnAction.menu.changeType': 'Changer le type',
  'import.columnAction.menu.remove': 'Retirer la colonne',
  'import.columnHeader.error.empty': 'Le nom ne peut pas être vide',
  'import.columnHeader.error.duplicate': 'Ce nom est déjà utilisé'
}

const baseColumnConfig: ColumnConfigOutput = {
  original_name: 'my_column',
  new_name: null,
  excluded: false,
  cast_type: null,
  filter: null
}

describe('ColumnHeaderComponent', () => {
  let outsidePointerEvents$: Subject<MouseEvent>
  let mockOverlayRef: OverlayRef

  function buildMockOverlay(): Overlay {
    outsidePointerEvents$ = new Subject<MouseEvent>()
    mockOverlayRef = {
      hasAttached: vi.fn(() => false),
      attach: vi.fn(),
      detach: vi.fn(),
      dispose: vi.fn(),
      outsidePointerEvents: vi.fn(() => outsidePointerEvents$.asObservable())
    } as unknown as OverlayRef

    const positionStrategy = {
      withPositions: vi.fn().mockReturnThis(),
      withPush: vi.fn().mockReturnThis()
    }
    return {
      position: vi.fn(() => ({
        flexibleConnectedTo: vi.fn(() => positionStrategy)
      })),
      create: vi.fn(() => mockOverlayRef),
      scrollStrategies: { close: vi.fn(() => ({})) }
    } as unknown as Overlay
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ColumnHeaderComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render the column name', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const input = compiled.querySelector('input') as HTMLInputElement
    expect(input?.value).toBe('my_column')
  })

  it('should render the new_name when set', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      new_name: 'renamed_column'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const input = compiled.querySelector('input') as HTMLInputElement
    expect(input?.value).toBe('renamed_column')
  })

  it('should render the action button', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const actionBtn = compiled.querySelector('[data-action-button]')
    expect(actionBtn).toBeTruthy()
  })

  it('should NOT show indicator dot when no actions are configured', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeNull()
  })

  it('should show indicator dot when filter is active', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      filter: { operator: 'contains', value: 'test' }
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeTruthy()
  })

  it('should show indicator dot when cast_type is set', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      cast_type: 'numeric'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeTruthy()
  })

  it('should open the action menu when action button is clicked', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    // Assign mock directly since the CDK Overlay DI may not be resolvable in jsdom.
    // TypeScript readonly is compile-time only, so this works at runtime.
    ;(fixture.componentInstance as any).overlay = buildMockOverlay()

    expect(fixture.componentInstance.isMenuOpen()).toBe(false)

    const compiled = fixture.nativeElement as HTMLElement
    const actionBtn = compiled.querySelector(
      '[data-action-button]'
    ) as HTMLElement
    actionBtn.click()
    fixture.detectChanges()

    expect(fixture.componentInstance.isMenuOpen()).toBe(true)
    expect(mockOverlayRef.attach).toHaveBeenCalled()
  })

  it('should emit actionMenuOpened when an action is selected from the open menu', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionMenuOpened.subscribe((a) => emitted.push(a))

    // Assign mock so that the overlay can open
    ;(fixture.componentInstance as any).overlay = buildMockOverlay()

    // Open the menu via button click
    const compiled = fixture.nativeElement as HTMLElement
    const actionBtn = compiled.querySelector(
      '[data-action-button]'
    ) as HTMLElement
    actionBtn.click()
    fixture.detectChanges()

    // Simulate menu action (overlay content is rendered by CDK outside the component)
    fixture.componentInstance.onMenuAction('remove')
    fixture.detectChanges()

    expect(emitted.length).toBeGreaterThan(0)
    expect(emitted[0]).toBe('remove')
  })

  // --- T022: Inline rename tests ---

  it('should have an editable name input when column is not excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    expect(nameInput).toBeTruthy()
    expect(nameInput.disabled).toBe(false)
  })

  it('should have a disabled name input when column is excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      excluded: true
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    expect(nameInput).toBeTruthy()
    expect(nameInput.disabled).toBe(true)
  })

  it('should emit nameChanged with the new valid name on input event', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.nameChanged.subscribe((n) => emitted.push(n))

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = 'new_name'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toEqual(['new_name'])
    expect(compiled.querySelector('[data-name-error]')).toBeNull()
  })

  it('should NOT emit nameChanged and should show error for empty name', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.nameChanged.subscribe((n) => emitted.push(n))

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = '   '
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(0)
    const error = compiled.querySelector('[data-name-error]')
    expect(error).toBeTruthy()
    expect(error?.textContent?.trim()).toContain('vide')
  })

  it('should NOT emit nameChanged and should show error for duplicate name', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.nameChanged.subscribe((n) => emitted.push(n))

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = 'other_col'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(0)
    const error = compiled.querySelector('[data-name-error]')
    expect(error).toBeTruthy()
    expect(error?.textContent?.trim()).toContain('déjà utilisé')
  })

  it('should show restore button (not action button) when column is excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      excluded: true
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-restore-button]')).toBeTruthy()
    expect(compiled.querySelector('[data-action-button]')).toBeNull()
  })

  it('should show action button (not restore button) when column is not excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-action-button]')).toBeTruthy()
    expect(compiled.querySelector('[data-restore-button]')).toBeNull()
  })

  // --- T026: Remove/restore behavior ---

  it('should apply opacity-50 styling to wrapper when column is excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      excluded: true
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    // The inner row div should have opacity-50 class when excluded
    const rowDiv = compiled.querySelector('.opacity-50')
    expect(rowDiv).toBeTruthy()
  })

  it('should NOT apply opacity-50 styling when column is not excluded', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('.opacity-50')).toBeNull()
  })

  it('should emit actionMenuOpened with "remove" when restore button is clicked', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      excluded: true
    })
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionMenuOpened.subscribe((a) => emitted.push(a))

    const restoreBtn = fixture.nativeElement.querySelector(
      '[data-restore-button]'
    ) as HTMLElement
    restoreBtn.click()
    fixture.detectChanges()

    expect(emitted).toEqual(['remove'])
  })

  it('should clear validation error when re-entering a valid name after error', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const nameInput = compiled.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement

    // First trigger an error
    nameInput.value = ''
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()
    expect(compiled.querySelector('[data-name-error]')).toBeTruthy()

    // Then type a valid name
    nameInput.value = 'valid_name'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()
    expect(compiled.querySelector('[data-name-error]')).toBeNull()
  })

  it('should emit nameValidationErrorChanged with the error string when name is empty', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.nameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    const nameInput = fixture.nativeElement.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = '   '
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toBeTruthy()
    expect(emitted[0]).toContain('vide')
  })

  it('should emit nameValidationErrorChanged with the error string when name is duplicate', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.nameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    const nameInput = fixture.nativeElement.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = 'other_col'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toBeTruthy()
    expect(emitted[0]).toContain('déjà utilisé')
  })

  it('should emit nameValidationErrorChanged with null when name is valid', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.nameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    const nameInput = fixture.nativeElement.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement
    nameInput.value = 'valid_name'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toBeNull()
  })

  it('should emit nameValidationErrorChanged null after emitting an error (error cleared)', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.componentRef.setInput('allColumnNames', ['my_column', 'other_col'])
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.nameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    const nameInput = fixture.nativeElement.querySelector(
      '[data-name-input]'
    ) as HTMLInputElement

    // Trigger error
    nameInput.value = ''
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    // Fix it
    nameInput.value = 'fixed_name'
    nameInput.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    expect(emitted).toHaveLength(2)
    expect(emitted[0]).toBeTruthy() // error
    expect(emitted[1]).toBeNull() // cleared
  })

  it('should close the menu on pointerdown outside the overlay (e.g. scroll initiation)', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    // Build a mock where hasAttached() tracks actual attach/detach calls
    let attached = false
    const localOverlayRef = {
      hasAttached: vi.fn(() => attached),
      attach: vi.fn(() => {
        attached = true
      }),
      detach: vi.fn(() => {
        attached = false
      }),
      dispose: vi.fn(),
      overlayElement: document.createElement('div')
    } as unknown as OverlayRef

    const positionStrategy = {
      withPositions: vi.fn().mockReturnThis(),
      withPush: vi.fn().mockReturnThis()
    }
    const localOverlay = {
      position: vi.fn(() => ({
        flexibleConnectedTo: vi.fn(() => positionStrategy)
      })),
      create: vi.fn(() => localOverlayRef),
      scrollStrategies: { close: vi.fn(() => ({})) }
    } as unknown as Overlay

    ;(fixture.componentInstance as any).overlay = localOverlay

    // Open the menu
    const actionBtn = fixture.nativeElement.querySelector(
      '[data-action-button]'
    ) as HTMLElement
    actionBtn.click()
    fixture.detectChanges()
    expect(fixture.componentInstance.isMenuOpen()).toBe(true)

    // Simulate a pointerdown outside the trigger and overlay (e.g. on a scrollable container)
    document.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    fixture.detectChanges()

    expect(fixture.componentInstance.isMenuOpen()).toBe(false)
    expect(localOverlayRef.detach).toHaveBeenCalled()
  })

  it('should NOT close the menu on pointerdown inside the trigger button', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    let attached = false
    const localOverlayRef = {
      hasAttached: vi.fn(() => attached),
      attach: vi.fn(() => {
        attached = true
      }),
      detach: vi.fn(() => {
        attached = false
      }),
      dispose: vi.fn(),
      overlayElement: document.createElement('div')
    } as unknown as OverlayRef

    const positionStrategy = {
      withPositions: vi.fn().mockReturnThis(),
      withPush: vi.fn().mockReturnThis()
    }
    const localOverlay = {
      position: vi.fn(() => ({
        flexibleConnectedTo: vi.fn(() => positionStrategy)
      })),
      create: vi.fn(() => localOverlayRef),
      scrollStrategies: { close: vi.fn(() => ({})) }
    } as unknown as Overlay

    ;(fixture.componentInstance as any).overlay = localOverlay

    // Open the menu
    const actionBtn = fixture.nativeElement.querySelector(
      '[data-action-button]'
    ) as HTMLElement
    actionBtn.click()
    fixture.detectChanges()
    expect(fixture.componentInstance.isMenuOpen()).toBe(true)

    // Simulate pointerdown on the trigger button itself — should NOT close
    actionBtn.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    fixture.detectChanges()

    expect(fixture.componentInstance.isMenuOpen()).toBe(true)
    expect(localOverlayRef.detach).not.toHaveBeenCalled()
  })
})
