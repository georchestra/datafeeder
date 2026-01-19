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

  it('should have file as default source type', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    expect(component.form.controls.radio.value).toBe('file')
  })

  it('should emit sourceChanged on form changes', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.sourceChanged.subscribe((value) => (emittedValue = value))
    component.form.controls.source.controls.url.setValue('https://test.com')

    expect(emittedValue).toEqual({
      type: 'file',
      file: null,
      url: 'https://test.com',
      authEnabled: false,
      username: null,
      password: null
    })
  })

  it('should remove the element when clicking on the remove button - file', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.source.controls.file.setValue(
      new File([], 'test.csv')
    )
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="remove-item"] > button'
    )
    expect(button).toBeTruthy()

    button.click()
    fixture.detectChanges()

    expect(component.form.controls.source.controls.file.value).toBeNull()
  })

  it('should remove the element when clicking on the remove button - url', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.source.controls.url.setValue('https://test.com')
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="remove-item"] > button'
    )

    button.click()
    fixture.detectChanges()

    expect(component.form.controls.source.controls.url.value).toBeNull()
  })

  describe('Basic Authentication', () => {
    it('should have authEnabled defaulting to false', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      expect(component.form.controls.source.controls.authEnabled.value).toBe(
        false
      )
    })

    it('should have null username and password by default', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      expect(component.form.controls.source.controls.username.value).toBeNull()
      expect(component.form.controls.source.controls.password.value).toBeNull()
    })

    it('should emit authEnabled when auth is toggled', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.sourceChanged.subscribe((value) => (emittedValue = value))
      component.form.controls.source.controls.authEnabled.setValue(true)
      expect(emittedValue.authEnabled).toBe(true)
    })

    it('should emit username and password when set', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.sourceChanged.subscribe((value) => (emittedValue = value))
      component.form.controls.source.controls.authEnabled.setValue(true)
      component.form.controls.source.controls.username.setValue('testuser')
      component.form.controls.source.controls.password.setValue('testpass')
      component.handleUrlChange('https://example.com')

      expect(emittedValue).toEqual({
        type: 'url',
        file: null,
        url: 'https://example.com',
        authEnabled: true,
        username: 'testuser',
        password: 'testpass'
      })
    })
  })
})
