import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideRouter, Router } from '@angular/router'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../../core/api/api'
import { OperationToastStore } from '../../../core/stores/operation-toast.store'
import { QuickCreationComponent } from './quick-creation.component'

const translations = {
  'quickImport.modeWithData': 'Créer avec données',
  'quickImport.modeEmpty': 'Créer sans donnée'
}

describe('QuickCreationComponent', () => {
  let fixture: ComponentFixture<QuickCreationComponent>
  let component: QuickCreationComponent
  let nativeEl: HTMLElement
  let router: Router
  let apiInvokeSpy: ReturnType<typeof vi.fn>

  beforeEach(async () => {
    apiInvokeSpy = vi.fn().mockResolvedValue({ id: 'test-uuid' })

    await TestBed.configureTestingModule({
      imports: [
        QuickCreationComponent,
        TranslateTestingModule.withTranslations({
          fr: translations
        }).withDefaultLanguage('fr')
      ],
      providers: [
        provideRouter([]),
        { provide: Api, useValue: { invoke: apiInvokeSpy } },
        OperationToastStore
      ]
    }).compileComponents()

    router = TestBed.inject(Router)
    fixture = TestBed.createComponent(QuickCreationComponent)
    component = fixture.componentInstance
    nativeEl = fixture.nativeElement
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('initial state', () => {
    it('does not show menu', () => {
      expect(component.isMenuOpen()).toBe(false)
    })

    it('is not submitting', () => {
      expect(component.submitting()).toBe(false)
    })
  })

  describe('import link', () => {
    it('renders a routerLink to /import', () => {
      fixture.detectChanges()
      const anchor = nativeEl.querySelector(
        'a[routerlink="/import"]'
      ) as HTMLAnchorElement
      expect(anchor).toBeTruthy()
    })
  })

  describe('toggleMenu', () => {
    it('opens the menu', () => {
      component.toggleMenu()
      expect(component.isMenuOpen()).toBe(true)
    })

    it('closes the menu on second call', () => {
      component.toggleMenu()
      component.toggleMenu()
      expect(component.isMenuOpen()).toBe(false)
    })

    it('does nothing while submitting', () => {
      component.submitting.set(true)
      component.toggleMenu()
      expect(component.isMenuOpen()).toBe(false)
    })
  })

  describe('closeMenu', () => {
    it('closes the menu', () => {
      component.isMenuOpen.set(true)
      component.closeMenu()
      expect(component.isMenuOpen()).toBe(false)
    })

    it('does nothing while submitting', () => {
      component.isMenuOpen.set(true)
      component.submitting.set(true)
      component.closeMenu()
      expect(component.isMenuOpen()).toBe(true)
    })
  })

  describe('createEmptyDataset', () => {
    let navigateSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      component.isMenuOpen.set(true)
      navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
    })

    it('calls the API', async () => {
      await component.createEmptyDataset()
      expect(apiInvokeSpy).toHaveBeenCalledOnce()
    })

    it('navigates to the edit page after success', async () => {
      await component.createEmptyDataset()
      expect(navigateSpy).toHaveBeenCalledWith(['/', 'test-uuid', 'edit'])
    })

    it('emits datasetCreated on success', async () => {
      let emitCount = 0
      component.datasetCreated.subscribe(() => emitCount++)
      await component.createEmptyDataset()
      expect(emitCount).toBe(1)
    })

    it('closes the menu after success', async () => {
      await component.createEmptyDataset()
      expect(component.isMenuOpen()).toBe(false)
    })

    it('resets submitting to false after success', async () => {
      await component.createEmptyDataset()
      expect(component.submitting()).toBe(false)
    })

    it('shows an error toast and closes menu on API failure', async () => {
      apiInvokeSpy.mockRejectedValue(new Error('network error'))
      const operationToastStore = TestBed.inject(OperationToastStore)
      const addSpy = vi.spyOn(operationToastStore, 'addError')

      await component.createEmptyDataset()

      expect(addSpy).toHaveBeenCalledWith('emptyDatasetCreate')
      expect(component.isMenuOpen()).toBe(false)
      expect(component.submitting()).toBe(false)
    })

    it('does nothing if already submitting', async () => {
      component.submitting.set(true)
      await component.createEmptyDataset()
      expect(apiInvokeSpy).not.toHaveBeenCalled()
    })
  })

  describe('backdrop click', () => {
    it('closes menu on backdrop click when not submitting', () => {
      component.isMenuOpen.set(true)
      fixture.detectChanges()

      const backdrop = nativeEl.querySelector('.fixed.inset-0') as HTMLElement
      backdrop.click()
      fixture.detectChanges()

      expect(component.isMenuOpen()).toBe(false)
    })

    it('keeps menu open on backdrop click while submitting', () => {
      component.isMenuOpen.set(true)
      component.submitting.set(true)
      fixture.detectChanges()

      const backdrop = nativeEl.querySelector('.fixed.inset-0') as HTMLElement
      backdrop.click()
      fixture.detectChanges()

      expect(component.isMenuOpen()).toBe(true)
    })
  })
})
