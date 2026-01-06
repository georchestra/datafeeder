import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { DataSourceSelectorComponent } from './data-source-selector.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

describe('DataSourceSelectorComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataSourceSelectorComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.chooseType':
              'Choose how you want to import your data'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should display the title', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain(
      'Choose how you want to import your data'
    )
  })

  it('should have url as default source type', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    expect(component.form.controls.sourceType.value).toBe('url')
  })

  it('should validate URL pattern - reject invalid URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('invalid')
    expect(component.form.controls.url.errors?.['pattern']).toBeTruthy()
  })

  it('should validate URL pattern - accept valid http URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('http://example.com')
    expect(component.form.controls.url.errors?.['pattern']).toBeFalsy()
  })

  it('should validate URL pattern - accept valid https URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('https://example.com')
    expect(component.form.controls.url.errors?.['pattern']).toBeFalsy()
  })

  it('should emit sourceChanged on form changes', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.sourceChanged.subscribe((value) => (emittedValue = value))
    component.form.controls.url.setValue('https://test.com')

    expect(emittedValue).toEqual({
      type: 'url',
      url: 'https://test.com',
      authEnabled: false,
      username: '',
      password: ''
    })
  })

  it('should sync input to form', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    fixture.componentRef.setInput('sourceData', {
      type: 'url',
      url: 'https://initial.com'
    })
    fixture.detectChanges()

    expect(component.form.controls.url.value).toBe('https://initial.com')
  })

  it('should remove the element when clicking on the remove button', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    fixture.componentRef.setInput('sourceData', {
      type: 'url',
      url: 'https://initial.com'
    })
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="remove-item"] > button'
    )
    expect(button).toBeTruthy()

    button.click()
    fixture.detectChanges()

    expect(component.form.controls.url.value).toBe('')
  })

  describe('Basic Authentication', () => {
    it('should have authEnabled defaulting to false', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      expect(component.form.controls.authEnabled.value).toBe(false)
    })

    it('should have empty username and password by default', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      expect(component.form.controls.username.value).toBe('')
      expect(component.form.controls.password.value).toBe('')
    })

    it('should emit authEnabled when auth is toggled', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.sourceChanged.subscribe((value) => (emittedValue = value))
      component.form.controls.authEnabled.setValue(true)

      expect(emittedValue.authEnabled).toBe(true)
    })

    it('should emit username and password when set', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.sourceChanged.subscribe((value) => (emittedValue = value))
      component.form.controls.url.setValue('https://example.com')
      component.form.controls.authEnabled.setValue(true)
      component.form.controls.username.setValue('testuser')
      component.form.controls.password.setValue('testpass')

      expect(emittedValue).toEqual({
        type: 'url',
        url: 'https://example.com',
        authEnabled: true,
        username: 'testuser',
        password: 'testpass'
      })
    })

    it('should sync auth fields from input', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      fixture.componentRef.setInput('sourceData', {
        type: 'url',
        url: 'https://secured.com',
        authEnabled: true,
        username: 'admin',
        password: 'secret'
      })
      fixture.detectChanges()

      expect(component.form.controls.authEnabled.value).toBe(true)
      expect(component.form.controls.username.value).toBe('admin')
      expect(component.form.controls.password.value).toBe('secret')
    })
  })
})
