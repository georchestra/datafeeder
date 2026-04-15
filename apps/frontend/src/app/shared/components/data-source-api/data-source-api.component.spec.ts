import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { DatasetServiceDistribution } from 'geonetwork-ui'
import {
  type ApiData,
  DataSourceApiComponent
} from './data-source-api.component'

const mockService: DatasetServiceDistribution = {
  type: 'service',
  url: new URL('https://example.com/oapif'),
  accessServiceProtocol: 'ogcFeatures',
  identifierInService: 'buildings'
}

describe('DataSourceApiComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataSourceApiComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({})
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should emit apiDataChanged when a service is selected', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    const component = fixture.componentInstance
    let emitted: ApiData | null | undefined

    component.apiDataChanged.subscribe((v) => (emitted = v))
    component.handleServiceChange(mockService)

    expect(emitted).toEqual({
      serviceUrl: 'https://example.com/oapif',
      layerName: 'buildings',
      serviceProtocol: 'ogcFeatures'
    })
  })

  it('should emit null when removeService is called', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    const component = fixture.componentInstance
    let emitted: ApiData | null | undefined

    component.apiDataChanged.subscribe((v) => (emitted = v))
    component.removeService()

    expect(emitted).toBeNull()
  })

  it('should always show the service input', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('gn-ui-online-service-resource-input')
    ).toBeTruthy()
  })

  it('should still show the service input after a layer is selected', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    const component = fixture.componentInstance

    component.handleServiceChange(mockService)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('gn-ui-online-service-resource-input')
    ).toBeTruthy()
  })

  it('should not show the card when no layer is selected', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-test="remove-item"]')
    ).toBeNull()
  })

  it('should show the card when a layer is selected', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    const component = fixture.componentInstance

    component.handleServiceChange(mockService)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-test="remove-item"]')
    ).toBeTruthy()
  })

  it('should initialize from initialValue input', () => {
    const fixture = TestBed.createComponent(DataSourceApiComponent)
    const component = fixture.componentInstance
    const initial: ApiData = {
      serviceUrl: 'https://example.com/wfs',
      layerName: 'roads',
      serviceProtocol: 'wfs'
    }

    fixture.componentRef.setInput('initialValue', initial)
    fixture.detectChanges()

    expect(component.selectedLayer()).toEqual(initial)
    expect(component.protocolLabel).toBe('WFS')
  })
})
