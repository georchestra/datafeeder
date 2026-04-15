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
      ftpHost: null,
      ftpPort: null,
      ftpPath: null,
      url: 'https://test.com',
      authEnabled: false,
      username: null,
      password: null,
      dbSchema: null,
      dbTable: null,
      serviceUrl: null,
      layerName: null,
      serviceProtocol: null
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

  describe('Database source', () => {
    it('should not show database radio when databaseSourceEnabled is false', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      fixture.componentRef.setInput('databaseSourceEnabled', false)
      fixture.detectChanges()

      const radioButtons =
        fixture.nativeElement.querySelectorAll('mat-radio-button')
      const labels = Array.from(radioButtons).map((rb: any) =>
        rb.getAttribute('value')
      )
      expect(labels).not.toContain('database')
    })

    it('should show database radio when databaseSourceEnabled is true', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      fixture.componentRef.setInput('databaseSourceEnabled', true)
      fixture.detectChanges()

      const radioButtons =
        fixture.nativeElement.querySelectorAll('mat-radio-button')
      const labels = Array.from(radioButtons).map((rb: any) =>
        rb.getAttribute('value')
      )
      expect(labels).toContain('database')
    })

    it('should emit database source data with schema and table', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.sourceChanged.subscribe((value: any) => (emittedValue = value))
      component.handleRadioChange('database')
      component.form.controls.source.controls.dbSchema.setValue('geo')
      component.form.controls.source.controls.dbTable.setValue('rivers')

      expect(emittedValue.type).toBe('database')
      expect(emittedValue.dbSchema).toBe('geo')
      expect(emittedValue.dbTable).toBe('rivers')
    })

    it('should clear database fields when switching to file', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleRadioChange('database')
      component.form.controls.source.controls.dbSchema.setValue('geo')
      component.form.controls.source.controls.dbTable.setValue('rivers')

      component.handleRadioChange('file')

      expect(component.form.controls.source.controls.dbSchema.value).toBeNull()
      expect(component.form.controls.source.controls.dbTable.value).toBeNull()
    })
  })

  describe('API (OGC service) source', () => {
    it('should always show the api radio button', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      fixture.detectChanges()

      const radioButtons =
        fixture.nativeElement.querySelectorAll('mat-radio-button')
      const values = Array.from(radioButtons).map((rb: any) =>
        rb.getAttribute('value')
      )
      expect(values).toContain('api')
    })

    it('should set source type to api when api radio is selected', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleRadioChange('api')

      expect(component.form.controls.source.controls.type.value).toBe('api')
    })

    it('should render app-data-source-api when api radio is selected', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleRadioChange('api')
      fixture.detectChanges()

      expect(
        fixture.nativeElement.querySelector('app-data-source-api')
      ).toBeTruthy()
    })

    it('should update serviceUrl, layerName and serviceProtocol via handleApiDataChange', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleApiDataChange({
        serviceUrl: 'https://example.com/wfs',
        layerName: 'ns:buildings',
        layerTitle: 'Buildings',
        serviceProtocol: 'wfs'
      })

      expect(component.form.controls.source.controls.serviceUrl.value).toBe(
        'https://example.com/wfs'
      )
      expect(component.form.controls.source.controls.layerName.value).toBe(
        'ns:buildings'
      )
      expect(
        component.form.controls.source.controls.serviceProtocol.value
      ).toBe('wfs')
    })

    it('should clear api fields when handleApiDataChange is called with null', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleApiDataChange({
        serviceUrl: 'https://example.com/wfs',
        layerName: 'ns:buildings',
        layerTitle: 'Buildings',
        serviceProtocol: 'wfs'
      })
      component.handleApiDataChange(null)

      expect(
        component.form.controls.source.controls.serviceUrl.value
      ).toBeNull()
      expect(component.form.controls.source.controls.layerName.value).toBeNull()
      expect(
        component.form.controls.source.controls.serviceProtocol.value
      ).toBeNull()
    })

    it('should emit sourceChanged with api fields after handleApiDataChange', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance
      let emittedValue: any

      component.handleRadioChange('api')
      component.sourceChanged.subscribe((value) => (emittedValue = value))

      component.handleApiDataChange({
        serviceUrl: 'https://example.com/ogcapi',
        layerName: 'parcels',
        layerTitle: 'City parcels',
        serviceProtocol: 'ogcFeatures'
      })

      expect(emittedValue.type).toBe('api')
      expect(emittedValue.serviceUrl).toBe('https://example.com/ogcapi')
      expect(emittedValue.layerName).toBe('parcels')
      expect(emittedValue.serviceProtocol).toBe('ogcFeatures')
    })

    it('should clear api fields when switching to file', () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      component.handleRadioChange('api')
      component.form.controls.source.patchValue({
        serviceUrl: 'https://example.com/wfs',
        layerName: 'ns:buildings',
        serviceProtocol: 'wfs'
      })

      component.handleRadioChange('file')

      expect(
        component.form.controls.source.controls.serviceUrl.value
      ).toBeNull()
      expect(component.form.controls.source.controls.layerName.value).toBeNull()
      expect(
        component.form.controls.source.controls.serviceProtocol.value
      ).toBeNull()
    })

    it('should pre-populate form from initialApiSource input', async () => {
      const fixture = TestBed.createComponent(DataSourceSelectorComponent)
      const component = fixture.componentInstance

      fixture.componentRef.setInput('initialApiSource', {
        url: 'https://example.com/wfs',
        layerName: 'ns:buildings',
        protocol: 'wfs'
      })
      fixture.detectChanges()
      await fixture.whenStable()

      expect(component.form.controls.radio.value).toBe('api')
      expect(component.form.controls.source.controls.serviceUrl.value).toBe(
        'https://example.com/wfs'
      )
      expect(component.form.controls.source.controls.layerName.value).toBe(
        'ns:buildings'
      )
      expect(
        component.form.controls.source.controls.serviceProtocol.value
      ).toBe('wfs')
    })
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
        ftpHost: null,
        ftpPort: null,
        ftpPath: null,
        url: 'https://example.com',
        authEnabled: true,
        username: 'testuser',
        password: 'testpass',
        dbSchema: null,
        dbTable: null,
        serviceUrl: null,
        layerName: null,
        serviceProtocol: null
      })
    })
  })
})
