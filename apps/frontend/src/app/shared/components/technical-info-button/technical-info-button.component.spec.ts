import { TestBed } from '@angular/core/testing'
import { Overlay, OverlayRef } from '@angular/cdk/overlay'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TechnicalInfoButtonComponent } from './technical-info-button.component'

const translations = {
  'import.dataSource.technicalInfo.button': 'Informations techniques',
  'import.dataSource.technicalInfo.title': 'Formats et limites pris en charge',
  'import.dataSource.technicalInfo.formats': 'Formats acceptés : CSV, GeoJSON',
  'import.dataSource.technicalInfo.maxSize':
    'Taille maximale : 50 Mo par fichier'
}

function buildMockOverlay(): { overlay: Overlay; overlayRef: OverlayRef } {
  let attached = false
  const overlayRef = {
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
    withPush: vi.fn().mockReturnThis(),
    setOrigin: vi.fn().mockReturnThis()
  }
  const overlay = {
    position: vi.fn(() => ({
      flexibleConnectedTo: vi.fn(() => positionStrategy)
    })),
    create: vi.fn(() => overlayRef),
    scrollStrategies: { close: vi.fn(() => ({})) }
  } as unknown as Overlay

  return { overlay, overlayRef }
}

describe('TechnicalInfoButtonComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TechnicalInfoButtonComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(TechnicalInfoButtonComponent)
    fixture.detectChanges()
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render the trigger button with an accessible label', () => {
    const fixture = TestBed.createComponent(TechnicalInfoButtonComponent)
    fixture.detectChanges()

    const btn = fixture.nativeElement.querySelector(
      '[data-test="technical-info-button"]'
    ) as HTMLElement
    expect(btn).toBeTruthy()
    expect(btn.getAttribute('aria-label')).toBe('Informations techniques')
  })

  it('should be closed initially (panel not attached)', () => {
    const fixture = TestBed.createComponent(TechnicalInfoButtonComponent)
    fixture.detectChanges()
    expect(fixture.componentInstance.isOpen()).toBe(false)
  })

  it('should open the panel when the button is clicked', () => {
    const fixture = TestBed.createComponent(TechnicalInfoButtonComponent)
    fixture.detectChanges()

    const { overlay, overlayRef } = buildMockOverlay()
    ;(fixture.componentInstance as any).overlay = overlay

    const btn = fixture.nativeElement.querySelector(
      '[data-test="technical-info-button"]'
    ) as HTMLElement
    btn.click()
    fixture.detectChanges()

    expect(fixture.componentInstance.isOpen()).toBe(true)
    expect(overlayRef.attach).toHaveBeenCalled()
  })

  it('should close the panel on pointerdown outside the button and overlay', () => {
    const fixture = TestBed.createComponent(TechnicalInfoButtonComponent)
    fixture.detectChanges()

    const { overlay, overlayRef } = buildMockOverlay()
    ;(fixture.componentInstance as any).overlay = overlay

    const btn = fixture.nativeElement.querySelector(
      '[data-test="technical-info-button"]'
    ) as HTMLElement
    btn.click()
    fixture.detectChanges()
    expect(fixture.componentInstance.isOpen()).toBe(true)

    document.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    fixture.detectChanges()

    expect(fixture.componentInstance.isOpen()).toBe(false)
    expect(overlayRef.detach).toHaveBeenCalled()
  })
})
