import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideRouter, Router } from '@angular/router'
import { TranslateTestingModule } from 'ngx-translate-testing'
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

  beforeEach(async () => {
    sessionStorage.clear()
    await TestBed.configureTestingModule({
      imports: [
<<<<<<< HEAD:apps/frontend/src/app/shared/components/quick-import/quick-import.component.spec.ts
        QuickImportComponent,
        TranslateTestingModule.withTranslations({
          fr: translations
        }).withDefaultLanguage('fr')
=======
        QuickCreationComponent,
        TranslateTestingModule.withTranslations({ fr: translations }).withDefaultLanguage('fr')
>>>>>>> adcad303 (refactor: rename quick import component > quick creation):apps/frontend/src/app/shared/components/quick-creation/quick-creation.component.spec.ts
      ],
      providers: [provideRouter([])]
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
    beforeEach(() => {
      component.triggerAction() // open form
    })

    it('does nothing when title is blank', async () => {
      const emitted: string[] = []
      component.datasetCreated.subscribe((v) => emitted.push(v))
      await component.submit()
      expect(emitted).toHaveLength(0)
    })

    it('emits datasetCreated with the title', async () => {
      const emitted: string[] = []
      component.datasetCreated.subscribe((v) => emitted.push(v))
      component.title.set('Mon dataset')
      await component.submit()
      expect(emitted).toEqual(['Mon dataset'])
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
