import { TestBed, fakeAsync, tick } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { DataImportWizardComponent } from './data-import-wizard.component'

describe('DataImportWizardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataImportWizardComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should initialize with first tab selected', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should initialize with empty source data', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.importData()).toEqual({
      source: { type: 'url', url: '' }
    })
  })

  it('should render both tab labels', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Ajouter un jeu de donnée')
    expect(compiled.textContent).toContain('Paramétrer le jeu de donnée')
  })

  it('should render tab icons', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    const icons = compiled.querySelectorAll('mat-icon')
    expect(icons.length).toBeGreaterThanOrEqual(2)
    expect(icons[0].textContent).toContain('add')
    expect(icons[1].textContent).toContain('settings')
  })

  it('should update import data when source changes', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({ type: 'url', url: 'https://test.com' })

    expect(component.importData().source).toEqual({
      type: 'url',
      url: 'https://test.com'
    })
  })

  it('should render data source selector in first tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-data-source-selector')).toBeTruthy()
  })

  it('should render dataset configuration in second tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Switch to second tab
    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-dataset-configuration')).toBeTruthy()
  })
})

describe('DataImportWizardComponent - URL Validation', () => {
  let httpMock: HttpTestingController

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataImportWizardComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    // Flush any non-cancelled pending requests before verification
    const pendingRequests = httpMock.match(() => true)
    pendingRequests.forEach((req) => {
      if (!req.cancelled) {
        req.flush(null, { status: 200, statusText: 'OK' })
      }
    })
    httpMock.verify() // Ensure no outstanding requests
  })

  it('should start with validSource as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.validSource()).toBe(false)
  })

  it('should start with validating as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.validating()).toBe(false)
  })

  it('should keep validSource false for invalid URL format', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({ type: 'url', url: 'invalid-url' })
    tick(300)

    expect(component.validSource()).toBe(false)
    expect(component.validating()).toBe(false)
  }))

  it('should keep validSource false for empty URL', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({ type: 'url', url: '' })
    tick(300)

    expect(component.validSource()).toBe(false)
    expect(component.validating()).toBe(false)
  }))

  it('should set validSource true for URL with 200 response', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    component.onSourceChanged({ type: 'url', url: 'https://test.com/data.csv' })
    fixture.detectChanges() // Trigger effect
    tick(300) // Wait for debounce

    const req = httpMock.expectOne('https://test.com/data.csv')
    expect(req.request.method).toBe('HEAD')
    req.flush(null, { status: 200, statusText: 'OK' })
    tick() // Process response

    expect(component.validSource()).toBe(true)
    expect(component.validating()).toBe(false)
  }))

  it('should set validSource false for URL with 404 response', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/missing.csv'
    })
    fixture.detectChanges() // Trigger effect
    tick(300) // Wait for debounce

    const req = httpMock.expectOne('https://test.com/missing.csv')
    expect(req.request.method).toBe('HEAD')
    req.flush(null, { status: 404, statusText: 'Not Found' })
    tick() // Process response

    expect(component.validSource()).toBe(false)
    expect(component.validating()).toBe(false)
  }))

  it('should set validSource false on HTTP error', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/error.csv'
    })
    fixture.detectChanges() // Trigger effect
    tick(300) // Wait for debounce

    const req = httpMock.expectOne('https://test.com/error.csv')
    req.error(new ProgressEvent('Network error'))
    tick() // Process error

    expect(component.validSource()).toBe(false)
    expect(component.validating()).toBe(false)
  }))

  it('should debounce requests by 300ms', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    // First change
    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/data1.csv'
    })
    fixture.detectChanges()
    tick(100)

    // Second change before debounce completes
    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/data2.csv'
    })
    fixture.detectChanges()
    tick(100)

    // Third change before debounce completes
    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/data3.csv'
    })
    fixture.detectChanges()
    tick(300)

    // Only the last URL should trigger a request
    const req = httpMock.expectOne('https://test.com/data3.csv')
    req.flush(null, { status: 200, statusText: 'OK' })
    tick() // Process response

    expect(component.validSource()).toBe(true)
  }))

  it('should set validating true during HTTP request', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    component.onSourceChanged({ type: 'url', url: 'https://test.com/data.csv' })
    fixture.detectChanges() // Trigger effect
    tick(300) // Wait for debounce

    // Before response, validating should be true
    expect(component.validating()).toBe(true)

    const req = httpMock.expectOne('https://test.com/data.csv')
    req.flush(null, { status: 200, statusText: 'OK' })
    tick() // Process response

    // After response, validating should be false
    expect(component.validating()).toBe(false)
  }))

  it('should disable button when validSource is false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validSource.set(false)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'button[mat-raised-button]'
    )
    expect(button.disabled).toBe(true)
  })

  it('should disable button when validating is true', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validating.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'button[mat-raised-button]'
    )
    expect(button.disabled).toBe(true)
  })

  it('should show "Validation..." text when validating', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validating.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'button[mat-raised-button]'
    )
    expect(button.textContent).toContain('Validation...')
  })

  it('should handle URL changes after request starts', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges() // Initialize component

    // Start first validation
    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/data1.csv'
    })
    fixture.detectChanges()
    tick(300) // First request is now pending

    // Change URL while first request is pending
    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com/data2.csv'
    })
    fixture.detectChanges()
    tick(300) // Second request is now pending

    // Both requests are in the mock
    const requests = httpMock.match(() => true)
    expect(requests.length).toBe(2)

    // Respond to non-cancelled requests only
    requests.forEach((req) => {
      if (!req.cancelled) {
        req.flush(null, { status: 200, statusText: 'OK' })
      }
    })
    tick() // Process responses

    // The final validSource should be true from the last request
    expect(component.validSource()).toBe(true)
  }))
})
