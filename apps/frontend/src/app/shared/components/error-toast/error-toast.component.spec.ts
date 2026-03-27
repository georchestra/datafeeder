import { TestBed } from '@angular/core/testing'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { ErrorToastComponent } from './error-toast.component'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'

const translations = {
  'errors.operation.metadataSave':
    'La sauvegarde des métadonnées a rencontré une erreur',
  'errors.operation.deletion': 'La suppression a rencontré une erreur'
}

describe('ErrorToastComponent', () => {
  let store: ErrorToastStore

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ErrorToastComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()

    store = TestBed.inject(ErrorToastStore)
  })

  it('should not render the overlay when no toasts', () => {
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()
    const overlay = fixture.nativeElement.querySelector(
      '[data-testid="error-toast-overlay"]'
    )
    expect(overlay).toBeNull()
  })

  it('should render a toast when one is added', () => {
    store.add('metadataSave')
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()
    const toasts = fixture.nativeElement.querySelectorAll(
      '[data-testid="error-toast"]'
    )
    expect(toasts).toHaveLength(1)
  })

  it('should render the translated message', () => {
    store.add('metadataSave')
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()
    const toast = fixture.nativeElement.querySelector(
      '[data-testid="error-toast"]'
    )
    expect(toast.textContent).toContain(
      'La sauvegarde des métadonnées a rencontré une erreur'
    )
  })

  it('should render multiple toasts in stacking order (oldest first)', () => {
    store.add('metadataSave')
    store.add('deletion')
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()
    const toasts = fixture.nativeElement.querySelectorAll(
      '[data-testid="error-toast"]'
    )
    expect(toasts).toHaveLength(2)
    expect(toasts[0].textContent).toContain(
      'La sauvegarde des métadonnées a rencontré une erreur'
    )
    expect(toasts[1].textContent).toContain(
      'La suppression a rencontré une erreur'
    )
  })

  it('should call store.remove when dismiss button is clicked', () => {
    store.add('metadataSave')
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()

    const dismissBtn = fixture.nativeElement.querySelector(
      '[data-testid="dismiss-button"]'
    )
    dismissBtn.click()
    fixture.detectChanges()

    expect(store.toasts()).toHaveLength(0)
  })

  it('should only remove the dismissed toast', () => {
    store.add('metadataSave')
    store.add('deletion')
    const fixture = TestBed.createComponent(ErrorToastComponent)
    fixture.detectChanges()

    const dismissBtns = fixture.nativeElement.querySelectorAll(
      '[data-testid="dismiss-button"]'
    )
    dismissBtns[0].click()
    fixture.detectChanges()

    const toasts = fixture.nativeElement.querySelectorAll(
      '[data-testid="error-toast"]'
    )
    expect(toasts).toHaveLength(1)
    expect(toasts[0].textContent).toContain(
      'La suppression a rencontré une erreur'
    )
  })
})
