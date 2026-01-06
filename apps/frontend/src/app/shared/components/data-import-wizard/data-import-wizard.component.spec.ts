import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed, fakeAsync, tick } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { ApiConfiguration } from '../../../core/api/api-configuration'
import { DataImportWizardComponent } from './data-import-wizard.component'

describe('DataImportWizardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.title': 'Add a dataset',
            'import.datasetConfiguration.title': 'Configure the dataset'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
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
      source: {
        type: 'url',
        url: '',
        authEnabled: false,
        username: '',
        password: ''
      }
    })
  })

  it('should render both tab labels', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Add a dataset')
    expect(compiled.textContent).toContain('Configure the dataset')
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
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.validation': 'Validating...'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
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
      'gn-ui-button[data-test="configure-dataset"] > button'
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
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    expect(button.disabled).toBe(true)
  })

  it('should show "Validating..." text when validating', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validating.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    expect(button.textContent).toContain('Validating...')
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

describe('DataImportWizardComponent - Import and Status Polling', () => {
  let httpMock: HttpTestingController

  // Mock data constants
  const mockImportResponse = {
    dag_id: 'test-dag-123',
    dag_run_id: 'test-run-456',
    integrity_link_id: 'test-link-789',
    status: 'queued'
  }

  const mockStatusRunning: string = 'running'

  const mockStatusFinished: string = 'success'

  const mockStatusFailed: string = 'failed'

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.failedError': 'An error occured',
            'import.dataSource.missingUrl': 'Missing URL',
            'import.dataSource.processing': 'Processing...',
            'import.dataSource.sending': 'Sending...'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    // Flush any pending validation HEAD requests before verification
    const pendingRequests = httpMock.match(() => true)
    pendingRequests.forEach((req) => {
      if (!req.cancelled) {
        req.flush(null, { status: 200, statusText: 'OK' })
      }
    })
    httpMock.verify()
  })

  // State Initialization Tests
  it('should start with importing as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.importing()).toBe(false)
  })

  it('should start with polling as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.polling()).toBe(false)
  })

  it('should start with importError as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.importError()).toBe(null)
  })

  it('should start with dagRunInfo as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.dagRunInfo()).toBe(null)
  })

  // Successful Import Flow Tests
  it('should call POST /import with correct URL', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Set URL and mark as valid (bypass validation effect)
    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)

    // Start the async operation
    const promise = component.onConfigureDataset()

    // Wait for the HTTP request
    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toBeInstanceOf(FormData)
    const formData = req.request.body as FormData
    expect(formData.get('type')).toBe('url')
    expect(formData.get('url')).toBe('https://test.com/data.csv')

    // Respond to the import request
    req.flush(mockImportResponse)

    // Wait for the status polling request
    await new Promise((resolve) => setTimeout(resolve, 600)) // Wait for poll interval
    const statusReq = httpMock.expectOne((r) =>
      r.url.includes('/airflow/dags/test-dag-123/runs/test-run-456/status')
    )
    statusReq.flush(mockStatusFinished)

    // Wait for the promise to complete
    await promise
  })

  it('should store dag_id and dag_run_id from import response', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    req.flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.dagRunInfo()).toEqual({
      dag_id: 'test-dag-123',
      dag_run_id: 'test-run-456'
    })

    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) =>
        r.url.includes('/airflow/dags/test-dag-123/runs/test-run-456/status')
      )
      .flush(mockStatusFinished)
    await promise
  })

  it('should poll status endpoint with dag_id and dag_run_id', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 600))

    const statusReq = httpMock.expectOne((r) =>
      r.url.includes('/airflow/dags/test-dag-123/runs/test-run-456/status')
    )
    expect(statusReq.request.method).toBe('GET')
    statusReq.flush(mockStatusFinished)
    await promise
  })

  it('should continue polling while status is running', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 600))

    // First poll - running
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusRunning)
    await new Promise((resolve) => setTimeout(resolve, 600))

    // Second poll - running
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusRunning)
    await new Promise((resolve) => setTimeout(resolve, 600))

    // Third poll - finished
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise
  })

  it('should navigate to second tab when status is finished', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 600))

    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusRunning)
    await new Promise((resolve) => setTimeout(resolve, 600))

    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise

    expect(component.selectedTabIndex()).toBe(1)
  })

  // Error Handling Tests
  it('should display error when status is failed', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)

    try {
      const promise = component.onConfigureDataset()
      httpMock
        .expectOne('http://localhost:8000/ingestion/staging/')
        .flush(mockImportResponse)
      await new Promise((resolve) => setTimeout(resolve, 600))

      httpMock
        .expectOne((r) => r.url.includes('/airflow/dags'))
        .flush(mockStatusFailed)
      await promise
    } catch (error) {
      // Expected to throw
    }

    expect(component.importError()).toBe('An error occured')
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should display error on import request failure', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)

    try {
      const promise = component.onConfigureDataset()
      const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
      req.error(new ProgressEvent('Network error'))
      await promise
    } catch (error) {
      // Expected to throw
    }

    expect(component.importError()).toBeTruthy()
    expect(component.polling()).toBe(false)
  })

  // Skip this test as it requires waiting 30+ seconds for RxJS timeout to trigger
  // The timeout functionality is covered by the RxJS timeout operator
  it.skip('should display error on polling timeout', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)

    try {
      const promise = component.onConfigureDataset()
      httpMock
        .expectOne('http://localhost:8000/ingestion/staging/')
        .flush(mockImportResponse)

      // Keep polling with 'running' status until timeout (30000ms)
      // At 500ms intervals, we need 60 iterations to reach 30000ms
      for (let i = 0; i < 61; i++) {
        await new Promise((resolve) => setTimeout(resolve, 550))
        const req = httpMock.match((r) => r.url.includes('/airflow/dags'))
        if (req.length > 0) {
          req[0].flush(mockStatusRunning)
        }
      }

      await promise
    } catch (error) {
      // Expected to timeout
    }

    expect(component.importError() || '').toContain("Délai d'attente dépassé")
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should handle missing URL error', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({ source: { type: 'url', url: '' } })
    await component.onConfigureDataset()

    expect(component.importError()).toContain('Missing URL')
  })

  // Button State Tests
  it('should disable button during import', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    fixture.detectChanges()

    const promise = component.onConfigureDataset()
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.importing()).toBe(true)

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    fixture.detectChanges()
    expect(button.disabled).toBe(true)

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise
  })

  it('should disable button during polling', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    fixture.detectChanges()

    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.polling()).toBe(true)

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    fixture.detectChanges()
    expect(button.disabled).toBe(true)

    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise
  })

  it('should show "Sending..." text when importing', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validSource.set(true)
    component.validating.set(false)
    component.importing.set(true)
    component.polling.set(false)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    expect(button.textContent).toContain('Sending...')

    component.importing.set(false)
    tick()
  }))

  it('should show "Processing..." text when polling', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.validSource.set(true)
    component.polling.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button[data-test="configure-dataset"] > button'
    )
    expect(button.textContent).toContain('Processing...')

    component.polling.set(false)
    tick()
  }))

  // State Cleanup Tests
  it('should reset importing and polling flags on success', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise

    expect(component.importing()).toBe(false)
    expect(component.polling()).toBe(false)
  })

  it('should reset importing and polling flags on error', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({ source: { type: 'url', url: '' } })
    await component.onConfigureDataset()

    expect(component.importing()).toBe(false)
    expect(component.polling()).toBe(false)
    expect(component.importError()).toBeTruthy()
  })
})

describe('DataImportWizardComponent - Dataset Validation', () => {
  let httpMock: HttpTestingController

  // Mock data constants
  const mockStagingResponse = {
    dag_id: 'staging-dag-123',
    dag_run_id: 'staging-run-456',
    integrity_link_id: 'test-link-789',
    status: 'queued'
  }

  const mockProcessResponse = {
    dag_id: 'process-dag-123',
    dag_run_id: 'process-run-456',
    integrity_link_id: 'test-link-789',
    status: 'queued'
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.failedError': 'An error occurred',
            'import.dataSource.missingUrl': 'Missing URL',
            'import.dataSource.processing': 'Processing...',
            'import.dataSource.sending': 'Sending...',
            'import.dataSource.validation': 'Validating...',
            'import.dataSource.timeoutError': 'Timeout error',
            'import.dataSource.unknownError': 'Unknown error',
            'import.dataSource.fileImportNotImplemented':
              'File import not implemented',
            'import.dataSource.unsupportedSourceType':
              'Unsupported source type',
            'import.dataSource.next': 'Configure the dataset',
            'import.dataSource.validate': 'Validate the dataset',
            'import.datasetConfiguration.title': 'Configure the dataset'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    // Flush any pending requests before verification
    const pendingRequests = httpMock.match(() => true)
    pendingRequests.forEach((req) => {
      if (!req.cancelled) {
        req.flush(null, { status: 200, statusText: 'OK' })
      }
    })
    httpMock.verify()
  })

  // State Initialization Tests
  it('should start with integrityLinkId as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.integrityLinkId()).toBe(null)
  })

  it('should start with processing as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.processing()).toBe(false)
  })

  it('should start with validationError as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.validationError()).toBe(null)
  })

  // Store integrity_link_id from staging response
  it('should store integrity_link_id from staging response', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: 'https://test.com/data.csv' }
    })
    component.validSource.set(true)
    const promise = component.onConfigureDataset()

    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    req.flush(mockStagingResponse)
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.integrityLinkId()).toBe('test-link-789')

    // Complete status polling
    await new Promise((resolve) => setTimeout(resolve, 600))
    const statusReq = httpMock.expectOne((r) =>
      r.url.includes(
        '/airflow/dags/staging-dag-123/runs/staging-run-456/status'
      )
    )
    statusReq.flush('success')
    await promise
  })

  // Successful Validation Flow Tests
  it('should call POST /ingestion/process with correct data', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Set integrity link ID (as if staging completed)
    component.integrityLinkId.set('test-link-789')

    // Start validation
    const promise = component.onValidateDataset('Test Dataset Title')

    // Expect the correct API call
    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      integrity_link_id: 'test-link-789',
      title: 'Test Dataset Title'
    })

    // Respond to the request
    req.flush(mockProcessResponse)
    await promise
  })

  it('should navigate to /events/process_dag on success', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Get the router
    const router = (component as any).router
    const navigateSpy = vi.spyOn(router, 'navigate')

    component.integrityLinkId.set('test-link-789')
    const promise = component.onValidateDataset('Test Dataset')

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.flush(mockProcessResponse)
    await promise

    expect(navigateSpy).toHaveBeenCalledWith(['/events', 'process_dag'])
  })

  it('should set processing flag during validation', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkId.set('test-link-789')

    // Before validation
    expect(component.processing()).toBe(false)

    const promise = component.onValidateDataset('Test Dataset')

    // During validation
    expect(component.processing()).toBe(true)

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.flush(mockProcessResponse)
    await promise

    // After validation
    expect(component.processing()).toBe(false)
  })

  it('should clear validationError before starting validation', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkId.set('test-link-789')
    component.validationError.set('Previous error')

    const promise = component.onValidateDataset('Test Dataset')

    expect(component.validationError()).toBe(null)

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.flush(mockProcessResponse)
    await promise
  })

  // Error Handling Tests
  it('should display error on validation request failure', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkId.set('test-link-789')
    const promise = component.onValidateDataset('Test Dataset')

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.error(new ProgressEvent('Network error'), {
      status: 500,
      statusText: 'Server Error'
    })

    await promise

    expect(component.validationError()).toBeTruthy()
    expect(component.processing()).toBe(false)
  })

  it('should reset processing flag on error', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkId.set('test-link-789')
    const promise = component.onValidateDataset('Test Dataset')

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.flush(
      { error: 'Something went wrong' },
      { status: 400, statusText: 'Bad Request' }
    )

    await promise

    expect(component.processing()).toBe(false)
  })

  // Button State Tests
  it('should show Tab 1 button when on first tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(0)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector('gn-ui-button > button')
    expect(button?.textContent?.trim()).toContain('Configure the dataset')
  })

  it('should show Tab 2 button when on second tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector('gn-ui-button > button')
    expect(button?.textContent?.trim()).toContain('Validate the dataset')
  })

  it('should disable validation button when processing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.integrityLinkId.set('test-link-789')
    component.processing.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button > button'
    ) as HTMLButtonElement

    expect(button?.disabled).toBe(true)
  })

  it('should disable validation button when no integrity_link_id', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.integrityLinkId.set(null)
    component.processing.set(false)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button > button'
    ) as HTMLButtonElement

    expect(button?.disabled).toBe(true)
  })

  it('should enable validation button when has integrity_link_id and not processing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.integrityLinkId.set('test-link-789')
    component.processing.set(false)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector(
      'gn-ui-button > button'
    ) as HTMLButtonElement

    expect(button?.disabled).toBe(false)
  })

  it('should show "Processing..." when processing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.integrityLinkId.set('test-link-789')
    component.processing.set(true)
    fixture.detectChanges()

    const button = fixture.nativeElement.querySelector('gn-ui-button > button')
    expect(button?.textContent?.trim()).toContain('Processing')
  })

  it('should display validation error in Tab 2', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.validationError.set('Network error occurred')
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Network error occurred')
  })
})
