import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideRouter, Router } from '@angular/router'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../../core/api/api'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'
import { QuickCreationComponent } from './quick-creation.component'

const translations = {
  'quickImport.modeEmpty': 'Créer sans donnée',
  'quickImport.modeWithData': 'Créer avec données',
  'quickImport.titleLabel': 'Titre',
  'quickImport.titlePlaceholder': 'Ex : Population',
  'quickImport.create': 'Créer'
}

describe('QuickCreationComponent', () => {
  let fixture: ComponentFixture<QuickCreationComponent>
  let component: QuickCreationComponent
  let nativeEl: HTMLElement
  let router: Router
  let apiInvokeSpy: ReturnType<typeof vi.fn>

  beforeEach(async () => {
    sessionStorage.clear()
    apiInvokeSpy = vi.fn().mockResolvedValue({ id: 'test-uuid' })

    await TestBed.configureTestingModule({
      imports: [
        QuickCreationComponent,
        TranslateTestingModule.withTranslations({ fr: translations }).withDefaultLanguage('fr')
      ],
      providers: [
        provideRouter([]),
        { provide: Api, useValue: { invoke: apiInvokeSpy } },
        ErrorToastStore
      ]
    }).compileComponents()

    router = TestBed.inject(Router)
    fixture = TestBed.createComponent(QuickCreationComponent)
    component = fixture.componentInstance
    nativeEl = fixture.nativeElement
    fixture.detectChanges()
  })

  afterEach(() => sessionStorage.clear())

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('initial state', () => {
    it('defaults to empty mode', () => {
      expect(component.mode()).toBe('empty')
    })

    it('restores mode from sessionStorage', async () => {
      sessionStorage.setItem('quickImport.mode', 'with-data')
      const fixture2 = TestBed.createComponent(QuickCreationComponent)
      fixture2.detectChanges()
      expect(fixture2.componentInstance.mode()).toBe('with-data')
    })

    it('shows modeEmpty label on the action button by default', () => {
      expect(nativeEl.textContent).toContain('Créer sans donnée')
    })

    it('does not show form or menu', () => {
      expect(component.isFormOpen()).toBe(false)
      expect(component.isMenuOpen()).toBe(false)
    })
  })

  describe('triggerAction – empty mode', () => {
    it('opens the form on first click', () => {
      component.triggerAction()
      expect(component.isFormOpen()).toBe(true)
    })

    it('closes the form on second click', () => {
      component.triggerAction()
      component.triggerAction()
      expect(component.isFormOpen()).toBe(false)
    })

    it('clears title when form closes', () => {
      component.triggerAction()
      component.title.set('test')
      component.triggerAction()
      expect(component.title()).toBe('')
    })
  })

  describe('triggerAction – with-data mode', () => {
    beforeEach(() => component.mode.set('with-data'))

    it('navigates to /import', async () => {
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      component.triggerAction()
      expect(spy).toHaveBeenCalledWith(['/', 'import'])
    })

    it('does not open the form', () => {
      vi.spyOn(router, 'navigate').mockResolvedValue(true)
      component.triggerAction()
      expect(component.isFormOpen()).toBe(false)
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
  })

  describe('selectMode', () => {
    it('updates the mode signal', () => {
      component.selectMode('with-data')
      expect(component.mode()).toBe('with-data')
    })

    it('persists choice in sessionStorage', () => {
      component.selectMode('with-data')
      expect(sessionStorage.getItem('quickImport.mode')).toBe('with-data')
    })

    it('closes the menu', () => {
      component.toggleMenu()
      component.selectMode('empty')
      expect(component.isMenuOpen()).toBe(false)
    })

    it('updates buttonLabel computed', () => {
      component.selectMode('with-data')
      expect(component.buttonLabel()).toBe('quickImport.modeWithData')
      component.selectMode('empty')
      expect(component.buttonLabel()).toBe('quickImport.modeEmpty')
    })
  })

  describe('submit', () => {
    let navigateSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      component.triggerAction() // open form
      navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
    })

    it('does nothing when title is blank', async () => {
      const emitted: string[] = []
      component.datasetCreated.subscribe((v) => emitted.push(v))
      await component.submit()
      expect(emitted).toHaveLength(0)
      expect(apiInvokeSpy).not.toHaveBeenCalled()
    })

    it('emits datasetCreated with the title', async () => {
      const emitted: string[] = []
      component.datasetCreated.subscribe((v) => emitted.push(v))
      component.title.set('Mon dataset')
      await component.submit()
      expect(emitted).toEqual(['Mon dataset'])
    })

    it('calls the API with the trimmed title', async () => {
      component.title.set('  Mon dataset  ')
      await component.submit()
      expect(apiInvokeSpy).toHaveBeenCalledOnce()
      const [, params] = apiInvokeSpy.mock.calls[0]
      expect(params.body.title).toBe('Mon dataset')
    })

    it('navigates to the edit page after submit', async () => {
      component.title.set('Mon dataset')
      await component.submit()
      expect(navigateSpy).toHaveBeenCalledWith(['/', 'test-uuid', 'edit'])
    })

    it('closes the form and resets title after submit', async () => {
      component.title.set('Mon dataset')
      await component.submit()
      expect(component.isFormOpen()).toBe(false)
      expect(component.title()).toBe('')
    })

    it('resets submitting to false after submit', async () => {
      component.title.set('Mon dataset')
      await component.submit()
      expect(component.submitting()).toBe(false)
    })

    it('shows an error toast and keeps form open on API failure', async () => {
      apiInvokeSpy.mockRejectedValue(new Error('network error'))
      const errorToastStore = TestBed.inject(ErrorToastStore)
      const addSpy = vi.spyOn(errorToastStore, 'add')

      component.title.set('Mon dataset')
      await component.submit()

      expect(addSpy).toHaveBeenCalledWith('emptyDatasetCreate', expect.any(Error))
      expect(component.isFormOpen()).toBe(true)
      expect(component.submitting()).toBe(false)
    })
  })

  describe('backdrop click', () => {
    it('closes form and menu on backdrop click', () => {
      component.isFormOpen.set(true)
      component.isMenuOpen.set(true)
      fixture.detectChanges()

      const backdrop = nativeEl.querySelector('.fixed.inset-0') as HTMLElement
      backdrop.click()
      fixture.detectChanges()

      expect(component.isFormOpen()).toBe(false)
      expect(component.isMenuOpen()).toBe(false)
    })
  })
})
