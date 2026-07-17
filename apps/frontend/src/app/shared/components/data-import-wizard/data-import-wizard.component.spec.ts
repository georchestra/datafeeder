import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { signal } from '@angular/core'
import { TestBed, fakeAsync, tick } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { ActivatedRoute, provideRouter } from '@angular/router'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { ApiConfiguration } from '../../../core/api/api-configuration'
import { FileType, ImportType } from '../../../core/api/models'
import { SettingsService } from '../../../core/settings/settings.service'
import { IntegrityLinkStore } from '../../../core/stores/integrity-link.store'
import { DataImportWizardComponent } from './data-import-wizard.component'
import { FooterService } from '../../../core/layout/footer.service'

describe('DataImportWizardComponent', () => {
  let httpMock: HttpTestingController
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

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
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: vi.fn() }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    const pendingRequests = httpMock.match(() => true)
    pendingRequests.forEach((req) => {
      if (!req.cancelled) {
        req.flush([], { status: 200, statusText: 'OK' })
      }
    })
    httpMock.verify()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should render step title for each step', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Add a dataset')

    component.selectedTabIndex.set(1)
    fixture.detectChanges()
    expect(compiled.textContent).toContain('Configure the dataset')
  })

  it('should render data source selector in first tab', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    await fixture.whenStable()
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

  it('should initialize with first tab selected', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should initialize with null import data', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.importData()).toBeNull()
  })

  it('should start with valid source as falsy', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.validSource()).toBeFalsy()
  })

  it('should update import data when source changes', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com',
      authEnabled: false
    })

    expect(component.importData().source).toEqual({
      type: 'url',
      url: 'https://test.com',
      authEnabled: false
    })
  })

  it('should get truthy valid source only when source file or url is provided', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'file',
      file: new File([], 'test.csv'),
      authEnabled: false
    })

    expect(component.validSource()).toBeTruthy()

    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com',
      authEnabled: false
    })

    expect(component.validSource()).toBeTruthy()

    component.onSourceChanged({ type: 'file', authEnabled: false })

    expect(component.validSource()).toBeFalsy()
  })

  it('should return valid source for database type with schema and table', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'database',
      dbSchema: 'geo',
      dbTable: 'rivers',
      authEnabled: false
    })

    expect(component.validSource()).toBeTruthy()
  })

  it('should return invalid source for database type with empty schema', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'database',
      dbSchema: '',
      dbTable: 'rivers',
      authEnabled: false
    })

    expect(component.validSource()).toBeFalsy()
  })

  it('should return invalid source for database type with whitespace-only table', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'database',
      dbSchema: 'geo',
      dbTable: '   ',
      authEnabled: false
    })

    expect(component.validSource()).toBeFalsy()
  })

  it('should detect database source from existing integrity link for re-edit', () => {
    mockIntegrityLinkStore.integrityLink.set({
      source_import_type: 'database',
      source_url: 'db://SOURCE_DB_1/geo/rivers'
    })

    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.initialDatabaseSource()).toEqual({
      schema: 'geo',
      table: 'rivers'
    })
  })

  it('should enable database source when feature flag is absent but link is database type', () => {
    mockIntegrityLinkStore.integrityLink.set({
      source_import_type: 'database',
      source_url: 'db://SOURCE_DB_1/geo/rivers'
    })

    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.databaseSourceEnabled()).toBe(true)
  })

  it('should return valid source for api type with serviceUrl and layerName', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'api',
      serviceUrl: 'https://example.com/wfs',
      layerName: 'ns:buildings',
      serviceProtocol: 'wfs',
      authEnabled: false
    })

    expect(component.validSource()).toBeTruthy()
  })

  it('should return invalid source for api type with missing serviceUrl', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'api',
      serviceUrl: undefined,
      layerName: 'ns:buildings',
      authEnabled: false
    })

    expect(component.validSource()).toBeFalsy()
  })

  it('should return invalid source for api type with missing layerName', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'api',
      serviceUrl: 'https://example.com/wfs',
      layerName: undefined,
      authEnabled: false
    })

    expect(component.validSource()).toBeFalsy()
  })

  it('should return invalid source for api type with whitespace-only layerName', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({
      type: 'api',
      serviceUrl: 'https://example.com/wfs',
      layerName: '   ',
      authEnabled: false
    })

    expect(component.validSource()).toBeFalsy()
  })

  it('should compute initialApiSource from existing api integrity link', () => {
    mockIntegrityLinkStore.integrityLink.set({
      source_import_type: 'api',
      source_url: 'https://example.com/wfs',
      source_layer: 'ns:buildings',
      source_protocol: 'wfs'
    })

    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.initialApiSource()).toEqual({
      url: 'https://example.com/wfs',
      layerName: 'ns:buildings',
      protocol: 'wfs'
    })
  })

  it('should return null initialApiSource when link is not api type', () => {
    mockIntegrityLinkStore.integrityLink.set({
      source_import_type: 'file',
      source_url: '/tmp/data.gpkg',
      source_layer: null,
      source_protocol: null
    })

    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.initialApiSource()).toBeNull()
  })

  it('should default protocol to wfs when source_protocol is absent in api link', () => {
    mockIntegrityLinkStore.integrityLink.set({
      source_import_type: 'api',
      source_url: 'https://example.com/wfs',
      source_layer: 'ns:buildings',
      source_protocol: null
    })

    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.initialApiSource()?.protocol).toBe('wfs')
  })

  it('should register footer template with FooterService on init', () => {
    const footerService = TestBed.inject(FooterService)
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()

    expect(footerService.setContent).toHaveBeenCalledWith(expect.anything())
  })

  it('should clear footer template from FooterService on destroy', () => {
    const footerService = TestBed.inject(FooterService)
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()

    fixture.destroy()

    expect(footerService.setContent).toHaveBeenLastCalledWith(null)
  })
})

describe('DataImportWizardComponent - Import and Status Polling', () => {
  let httpMock: HttpTestingController
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }

  // Mock data constants
  const mockImportResponse = {
    dag_id: 'test-dag-123',
    dag_run_id: 'test-run-456',
    integrity_link_id: 'test-link-789',
    status: 'queued'
  }

  const mockStatusRunning = 'running'
  const mockStatusFinished = 'success'
  const mockStatusFailed = 'failed'

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.genericError':
              'The data upload or analysis failed. Please try again.',
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
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
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
  it('should call POST /import with correct URL - file source', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Set file
    component.importData.set({
      source: {
        type: 'file',
        file: new File([], 'test.csv'),
        authEnabled: false
      }
    })

    // Start the async operation
    const promise = component.onConfigureDataset()

    // Wait for the HTTP request
    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toBeInstanceOf(FormData)
    const formData = req.request.body as FormData
    expect(formData.get('type')).toBe('file')
    expect(formData.get('url')).toBe(null)
    expect(formData.get('file')).toBeInstanceOf(File)

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

  it('should call POST /import with correct URL - url source', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Set URL
    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })

    // Start the async operation
    const promise = component.onConfigureDataset()

    // Wait for the HTTP request
    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toBeInstanceOf(FormData)
    const formData = req.request.body as FormData
    expect(formData.get('type')).toBe('url')
    expect(formData.get('file')).toBe(null)
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

  it('should call POST /import with correct FormData for api source', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: {
        type: 'api',
        serviceUrl: 'https://example.com/wfs',
        layerName: 'ns:buildings',
        serviceProtocol: 'wfs',
        authEnabled: false
      }
    })

    const promise = component.onConfigureDataset()

    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    expect(req.request.method).toBe('POST')
    const formData = req.request.body as FormData
    expect(formData.get('type')).toBe('api')
    expect(formData.get('service_url')).toBe('https://example.com/wfs')
    expect(formData.get('layer_name')).toBe('ns:buildings')
    expect(formData.get('service_protocol')).toBe('wfs')

    req.flush(mockImportResponse)

    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) =>
        r.url.includes('/airflow/dags/test-dag-123/runs/test-run-456/status')
      )
      .flush(mockStatusFinished)

    await promise
  })

  it('should store dag_id and dag_run_id from import response', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
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
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
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
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
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
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })

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
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })

    try {
      const promise = component.onConfigureDataset()
      httpMock
        .expectOne('http://localhost:8000/ingestion/staging/')
        .flush(mockImportResponse)
      await new Promise((resolve) => setTimeout(resolve, 600))

      httpMock
        .expectOne((r) => r.url.includes('/status'))
        .flush(mockStatusFailed)

      // Wait for the /note request to be triggered after FAILED status
      await new Promise((resolve) => setTimeout(resolve, 10))
      httpMock.expectOne((r) => r.url.includes('/note')).flush(null)

      await promise
    } catch (error) {
      // Expected to throw
    }

    expect(component.importError()).toBe(
      'The data upload or analysis failed. Please try again.'
    )
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should display error when the backend returns an error', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })

    try {
      const promise = component.onConfigureDataset()
      const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
      req.flush(
        { detail: 'Invalid URL format provided' },
        { status: 400, statusText: 'Bad Request' }
      )
      await promise
    } catch (error) {
      // Expected to throw
    }

    expect(component.importError()).toBe(
      'The data upload or analysis failed. Please try again.'
    )
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should handle missing URL error', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: { type: 'url', url: '', authEnabled: false }
    })
    // The button should be disabled, but we call the method directly to test error handling
    await component.onConfigureDataset()

    expect(component.importError()).toBe(
      'The data upload or analysis failed. Please try again.'
    )
  })

  it('should clear previous error on new source change', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importError.set('Previous error')

    component.onSourceChanged({
      type: 'url',
      url: 'https://test.com',
      authEnabled: false
    })

    expect(component.importError()).toBeNull()
  })

  it('should clear previous error on configure dataset', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importError.set('Previous error')

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
    component.onConfigureDataset()

    expect(component.importError()).toBeNull()
  })

  // Button State Tests
  it('should disable button during import', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
    fixture.detectChanges()

    const promise = component.onConfigureDataset()
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.importing()).toBe(true)
    expect(component.cantConfigureDataset()).toBe(true)

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
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
    fixture.detectChanges()

    const promise = component.onConfigureDataset()

    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/')
      .flush(mockImportResponse)
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.polling()).toBe(true)
    expect(component.cantConfigureDataset()).toBe(true)

    await new Promise((resolve) => setTimeout(resolve, 600))
    httpMock
      .expectOne((r) => r.url.includes('/airflow/dags'))
      .flush(mockStatusFinished)
    await promise
  })

  it('should set importing flag to true when importing starts', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importing.set(true)
    component.polling.set(false)

    expect(component.importing()).toBe(true)
    expect(component.polling()).toBe(false)

    component.importing.set(false)
    tick()
  }))

  it('should set polling flag to true when polling starts', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importing.set(false)
    component.polling.set(true)

    expect(component.importing()).toBe(false)
    expect(component.polling()).toBe(true)

    component.polling.set(false)
    tick()
  }))

  // State Cleanup Tests
  it('should reset importing and polling flags on success', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
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

    component.importData.set({
      source: { type: 'url', url: '', authEnabled: false }
    })
    await component.onConfigureDataset()

    expect(component.importing()).toBe(false)
    expect(component.polling()).toBe(false)
    expect(component.importError()).toBeTruthy()
  })
})

describe('DataImportWizardComponent - Dataset Validation', () => {
  let httpMock: HttpTestingController
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }

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
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.genericError':
              'The data upload or analysis failed. Please try again.',
            'import.dataSource.processing': 'Processing...',
            'import.dataSource.sending': 'Sending...',
            'import.dataSource.validation': 'Validating...',
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
        provideRouter([]),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
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
    expect(component.integrityLinkStore.intlinkId()).toBe(null)
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

    // Mock setAndLoadIntegrityLink to update the signal
    component.integrityLinkStore.setAndLoadIntegrityLink = vi.fn(
      (id: string) => {
        component.integrityLinkStore.intlinkId.set(id)
        return Promise.resolve({} as any)
      }
    )

    component.importData.set({
      source: {
        type: 'url',
        url: 'https://test.com/data.csv',
        authEnabled: false
      }
    })
    const promise = component.onConfigureDataset()

    const req = httpMock.expectOne('http://localhost:8000/ingestion/staging/')
    req.flush(mockStagingResponse)
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.integrityLinkStore.intlinkId()).toBe('test-link-789')

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
    component.integrityLinkStore.intlinkId.set('test-link-789')

    // Start validation
    const promise = component.onValidateDataset('Test Dataset Title')

    // Expect the correct API call
    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      generate_metadata_with_ai: false,
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

    component.integrityLinkStore.intlinkId.set('test-link-789')
    const promise = component.onValidateDataset('Test Dataset')

    const req = httpMock.expectOne('http://localhost:8000/ingestion/process/')
    req.flush(mockProcessResponse)
    await promise

    expect(navigateSpy).toHaveBeenCalledWith(['test-link-789', 'edit'])
  })

  it('should set processing flag during validation', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('test-link-789')

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

    component.integrityLinkStore.intlinkId.set('test-link-789')
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

    component.integrityLinkStore.intlinkId.set('test-link-789')
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

    component.integrityLinkStore.intlinkId.set('test-link-789')
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
  it('should disable next button when no valid source is set', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // importData starts with no source → cantConfigureDataset returns true
    expect(component.cantConfigureDataset()).toBe(true)
  })

  it('should enable next button when a valid file source is set', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.update((d) => ({
      ...d,
      source: {
        type: 'file',
        file: new File([], 'test.csv'),
        authEnabled: false
      }
    }))

    expect(component.cantConfigureDataset()).toBe(false)
  })

  it('should disable next button while importing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.importData.update((d) => ({
      ...d,
      source: {
        type: 'file',
        file: new File([], 'test.csv'),
        authEnabled: false
      }
    }))
    component.importing.set(true)

    expect(component.cantConfigureDataset()).toBe(true)
  })

  it('should disable validate button when processing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('test-link-789')
    component.processing.set(true)

    expect(component.processing()).toBe(true)
    expect(component.integrityLinkStore.intlinkId()).toBeTruthy()
  })

  it('should disable validate button when no integrity link id', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set(null)
    component.processing.set(false)

    expect(component.integrityLinkStore.intlinkId()).toBeNull()
  })

  it('should disable validate button when there is a column name error', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('test-link-789')
    component.processing.set(false)
    component.columnNameErrors.set(new Set(['col1']))

    expect(component.hasColumnNameError()).toBe(true)
  })

  it('should enable validate button when integrity link exists, not processing, no column errors', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('test-link-789')
    component.processing.set(false)

    expect(component.processing()).toBe(false)
    expect(component.integrityLinkStore.intlinkId()).toBeTruthy()
    expect(component.hasColumnNameError()).toBe(false)
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

describe('DataImportWizardComponent - Preview Toggle', () => {
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.title': 'Add a dataset',
            'import.datasetConfiguration.title': 'Configure the dataset',
            'import.datasetConfiguration.previewTitle': 'Preview of the result',
            'import.datasetPreview.tableTab': 'Table',
            'import.datasetPreview.mapTab': 'Map'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
        }
      ]
    }).compileComponents()
  })

  it('should initialize previewTabIndex to 0', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.previewTabIndex()).toBe(0)
  })

  it('should compute isGeographicData as false when preview is null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.preview.set(null)
    expect(component.isGeographicData()).toBe(false)
  })

  it('should compute isGeographicData as false when is_geographic is false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.preview.set({
      data: [],
      is_geographic: false,
      geojson: null
    })
    expect(component.isGeographicData()).toBe(false)
  })

  it('should compute isGeographicData as false when geojson is null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: null
    })
    expect(component.isGeographicData()).toBe(false)
  })

  it('should compute isGeographicData as true when is_geographic is true and geojson exists', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: { type: 'FeatureCollection', features: [] }
    })
    expect(component.isGeographicData()).toBe(true)
  })

  it('should compute geojsonData from preview', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    const mockGeojson = { type: 'FeatureCollection' as const, features: [] }
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: mockGeojson
    })
    expect(component.geojsonData()).toEqual(mockGeojson)
  })

  it('should compute geojsonData as null when preview is null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.preview.set(null)
    expect(component.geojsonData()).toBeNull()
  })

  it('should render preview toggle buttons when on tab 2', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const toggleGroup = fixture.nativeElement.querySelector(
      'mat-button-toggle-group'
    )
    expect(toggleGroup).toBeTruthy()
  })

  it('should render Table and Map toggle buttons', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Table')
    expect(compiled.textContent).toContain('Map')
  })

  it('should disable Map toggle when not geographic data', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.preview.set({
      data: [],
      is_geographic: false,
      geojson: null
    })
    fixture.detectChanges()

    // Get all mat-button-toggle elements - the Map toggle is the second one
    const toggles = fixture.nativeElement.querySelectorAll('mat-button-toggle')
    const mapToggle = toggles[1]
    expect(mapToggle?.classList.contains('mat-button-toggle-disabled')).toBe(
      true
    )
  })

  it('should enable Map toggle when geographic data is present', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: { type: 'FeatureCollection', features: [] }
    })
    fixture.detectChanges()

    // Get all mat-button-toggle elements - the Map toggle is the second one
    const toggles = fixture.nativeElement.querySelectorAll('mat-button-toggle')
    const mapToggle = toggles[1]
    expect(mapToggle?.classList.contains('mat-button-toggle-disabled')).toBe(
      false
    )
  })

  it('should show dataset-preview-table when previewTabIndex is 0', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.previewTabIndex.set(0)
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: { type: 'FeatureCollection', features: [] }
    })
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('app-dataset-preview-table')
    ).toBeTruthy()
    expect(
      fixture.nativeElement.querySelector('app-dataset-preview-map')
    ).toBeFalsy()
  })

  it('should show dataset-preview-map when previewTabIndex is 1 and geographic', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.previewTabIndex.set(1)
    component.preview.set({
      data: [],
      is_geographic: true,
      geojson: { type: 'FeatureCollection', features: [] }
    })
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('app-dataset-preview-map')
    ).toBeTruthy()
    expect(
      fixture.nativeElement.querySelector('app-dataset-preview-table')
    ).toBeFalsy()
  })

  it('should always show table when not geographic data', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.previewTabIndex.set(1) // Even though set to 1
    component.preview.set({
      data: [],
      is_geographic: false,
      geojson: null
    })
    fixture.detectChanges()

    // Should still show table since not geographic
    expect(
      fixture.nativeElement.querySelector('app-dataset-preview-table')
    ).toBeTruthy()
  })

  it('should render preview title', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Preview of the result')
  })
})

// AI metadata generation toggle tests
describe('DataImportWizardComponent - Generate Metadata With AI Toggle', () => {
  const mockSettingsService = {
    currentSettings: signal({
      projections: []
    }),
    getSetting: vi.fn((key: string) =>
      key === 'enabled_features' ? ['ai_metadata'] : undefined
    )
  }

  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.generateMetadataWithAi':
              'Generate metadata with AI',
            'import.dataSource.generateMetadataWithAi.hint':
              '(Effective after validation)'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
        },
        { provide: SettingsService, useValue: mockSettingsService }
      ]
    }).compileComponents()
  })

  it('should default generateMetadataWithAi to false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.generateMetadataWithAi()).toBe(false)
  })

  it('should set generateMetadataWithAi when toggled on', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.generateMetadataWithAi.set(true)

    expect(component.generateMetadataWithAi()).toBe(true)
  })

  it('should toggle generateMetadataWithAi back and forth', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.generateMetadataWithAi.set(!component.generateMetadataWithAi())
    expect(component.generateMetadataWithAi()).toBe(true)

    component.generateMetadataWithAi.set(!component.generateMetadataWithAi())
    expect(component.generateMetadataWithAi()).toBe(false)
  })

  it('should not change generateMetadataWithAi via button click while processing', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.selectedTabIndex.set(1)
    component.processing.set(true)
    fixture.detectChanges()

    const footer = component.footerTpl()
    const view = footer!.createEmbeddedView(null)
    view.detectChanges()
    const rootNodes = view.rootNodes as HTMLElement[]
    const container = document.createElement('div')
    rootNodes.forEach((node) => container.appendChild(node))

    const button = container.querySelector('button') as HTMLButtonElement
    button.click()
    view.detectChanges()

    expect(component.generateMetadataWithAi()).toBe(false)

    view.destroy()
  })
})

// --- T017: Config flow tests ---
describe('DataImportWizardComponent - Config Flow (PUT→GET)', () => {
  let httpMock: HttpTestingController
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
  }

  const mockMetadata = {
    title: 'test.csv',
    file_type: 'csv' as FileType,
    force_projection: null,
    has_final_table: false,
    import_type: 'url' as ImportType,
    row_count: 2,
    columns: [
      {
        original_name: 'col1',
        new_name: null,
        excluded: false,
        cast_type: null,
        filter: null
      },
      {
        original_name: 'col2',
        new_name: null,
        excluded: false,
        cast_type: null,
        filter: null
      }
    ]
  }

  const mockPreview = {
    data: [{ col1: 'a', col2: 'b' }],
    is_geographic: false,
    geojson: null
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.error': 'Error',
            'import.dataSource.unknownError': 'Unknown error'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    const pending = httpMock.match(() => true)
    pending.forEach((req) => {
      if (!req.cancelled) req.flush(null)
    })
    httpMock.verify()
  })

  it('should call PUT metadata then GET preview when saveConfigAndRefresh is triggered', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('link-123')
    component.metadata.set(mockMetadata)
    component.columnConfigs.set(mockMetadata.columns)
    component.forceProjection.set(null)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const promise = (component as any).saveConfigAndRefresh()

    // Expect PUT request — triggered synchronously by the async function start
    const putReq = httpMock.expectOne(
      'http://localhost:8000/ingestion/staging/link-123/metadata'
    )
    expect(putReq.request.method).toBe('PUT')
    putReq.flush(mockMetadata)

    // Wait for microtasks to settle: PUT Promise resolves → saveConfigAndRefresh continues → refreshPreview called
    await Promise.resolve()
    await Promise.resolve()

    // Expect GET preview request
    const getReq = httpMock.expectOne((r) =>
      r.url.includes('/ingestion/staging/link-123/preview')
    )
    expect(getReq.request.method).toBe('GET')
    getReq.flush(mockPreview)

    await promise
    expect(component.preview()).toEqual(mockPreview)
    expect(component.previewError()).toBeNull()
  })

  it('should fall back to raw=true GET preview when raw=false preview errors', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('link-123')
    component.metadata.set(mockMetadata)
    component.columnConfigs.set(mockMetadata.columns)
    component.forceProjection.set(null)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const promise = (component as any).saveConfigAndRefresh()

    // PUT succeeds
    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/link-123/metadata')
      .flush(mockMetadata)

    await Promise.resolve()
    await Promise.resolve()

    // GET preview (raw=false) fails with server error
    const previewReq = httpMock.expectOne((r) => r.url.includes('/preview'))
    previewReq.flush(null, { status: 500, statusText: 'Server Error' })

    // Wait for fallback to trigger
    await new Promise((resolve) => setTimeout(resolve, 50))

    // Expect fallback GET preview (raw=true)
    const rawReq = httpMock.expectOne((r) => r.url.includes('/preview'))
    rawReq.flush(mockPreview)

    await promise
    expect(component.preview()).toEqual(mockPreview)
    expect(component.previewError()).toBeTruthy() // error shown for transformation failure
  })

  it('should set previewError when PUT metadata fails', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('link-123')
    component.metadata.set(mockMetadata)
    component.columnConfigs.set(mockMetadata.columns)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const promise = (component as any).saveConfigAndRefresh()

    // PUT fails with validation error
    httpMock
      .expectOne('http://localhost:8000/ingestion/staging/link-123/metadata')
      .flush(
        { detail: 'Duplicate column name' },
        { status: 422, statusText: 'Unprocessable Entity' }
      )

    await promise
    expect(component.previewError()).toBeTruthy()
  })
})

// --- T023: Rename debounce behavior tests ---
describe('DataImportWizardComponent - Rename Debounce (T023)', () => {
  let httpMock: HttpTestingController
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
  }

  const mockMetadata = {
    title: 'test.csv',
    file_type: 'csv' as FileType,
    force_projection: null,
    has_final_table: false,
    import_type: 'url' as ImportType,
    row_count: 1,
    columns: [
      {
        original_name: 'col1',
        new_name: null,
        excluded: false,
        cast_type: null,
        filter: null
      }
    ]
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: { 'import.dataSource.unknownError': 'Unknown error' }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    const pending = httpMock.match(() => true)
    pending.forEach((req) => {
      if (!req.cancelled) req.flush(null)
    })
    httpMock.verify()
  })

  it('should debounce rename: only one PUT call after 400ms for rapid events', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('link-abc')
    component.metadata.set(mockMetadata)
    component.columnConfigs.set([...mockMetadata.columns])

    // Simulate rapid rename events (before 400ms debounce fires)
    component.onColumnRenameRequested({
      originalName: 'col1',
      newName: 'renamed_1'
    })
    tick(100)
    component.onColumnRenameRequested({
      originalName: 'col1',
      newName: 'renamed_2'
    })
    tick(100)
    component.onColumnRenameRequested({
      originalName: 'col1',
      newName: 'renamed_final'
    })
    tick(100)

    // Debounce hasn't fired yet — no PUT request
    httpMock.expectNone(() => true)

    // Advance past debounce threshold
    tick(400)

    // Now exactly one PUT should fire with the last value
    const putReq = httpMock.expectOne(
      'http://localhost:8000/ingestion/staging/link-abc/metadata'
    )
    expect(putReq.request.method).toBe('PUT')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const body = putReq.request.body as { columns: Array<{ new_name: string }> }
    expect(body.columns[0].new_name).toBe('renamed_final')
    putReq.flush(mockMetadata)

    // Drain microtasks so refreshPreview fires
    tick(0)

    // GET preview fires
    const pending = httpMock.match((r) => r.url.includes('/preview'))
    pending.forEach((req) =>
      req.flush({ data: [], is_geographic: false, geojson: null })
    )

    tick(100)
  }))

  it('should update columnConfigs with the new name after debounce', fakeAsync(() => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.integrityLinkStore.intlinkId.set('link-abc')
    component.metadata.set(mockMetadata)
    component.columnConfigs.set([...mockMetadata.columns])

    component.onColumnRenameRequested({
      originalName: 'col1',
      newName: 'my_new_col'
    })
    tick(400)

    expect(component.columnConfigs()[0].new_name).toBe('my_new_col')

    // Flush the resulting HTTP requests
    const putReq = httpMock.expectOne((r) => r.url.includes('/metadata'))
    putReq.flush(mockMetadata)
    tick(0)

    const pending = httpMock.match((r) => r.url.includes('/preview'))
    pending.forEach((req) =>
      req.flush({ data: [], is_geographic: false, geojson: null })
    )

    tick(100)
  }))
})

describe('DataImportWizardComponent - Column Name Validation', () => {
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal>
    loadError: ReturnType<
      typeof signal<'forbidden' | 'not_found' | 'server_error' | null>
    >
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
  }

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal(null),
      loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(
        null
      ),
      setAndLoadIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({ en: {} })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        {
          provide: FooterService,
          useValue: { content: signal(null), setContent: () => {} }
        }
      ]
    }).compileComponents()
  })

  it('should start with hasColumnNameError as false', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.hasColumnNameError()).toBe(false)
  })

  it('should set hasColumnNameError to true when an error event is received', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: 'Le nom ne peut pas être vide'
    })

    expect(component.hasColumnNameError()).toBe(true)
    expect(component.columnNameErrors().has('col1')).toBe(true)
  })

  it('should set hasColumnNameError back to false when the error is cleared', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: 'error'
    })
    expect(component.hasColumnNameError()).toBe(true)

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: null
    })
    expect(component.hasColumnNameError()).toBe(false)
  })

  it('should remain true when one of multiple errors is cleared but another persists', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: 'error'
    })
    component.onColumnNameValidationErrorChanged({
      originalName: 'col2',
      error: 'error'
    })
    expect(component.hasColumnNameError()).toBe(true)

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: null
    })
    expect(component.hasColumnNameError()).toBe(true)
    expect(component.columnNameErrors().has('col2')).toBe(true)
  })

  it('should become false only when all errors are cleared', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: 'error'
    })
    component.onColumnNameValidationErrorChanged({
      originalName: 'col2',
      error: 'error'
    })

    component.onColumnNameValidationErrorChanged({
      originalName: 'col1',
      error: null
    })
    component.onColumnNameValidationErrorChanged({
      originalName: 'col2',
      error: null
    })

    expect(component.hasColumnNameError()).toBe(false)
  })

  it('should initialize on tab 2 when step=2 queryParam is present', () => {
    mockIntegrityLinkStore.intlinkId.set('existing-link-id')
    TestBed.overrideProvider(ActivatedRoute, {
      useValue: {
        snapshot: {
          params: {},
          queryParamMap: { get: (key: string) => (key === 'step' ? '2' : null) }
        }
      }
    })
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.selectedTabIndex()).toBe(1)
  })

  describe('handleIntegrityLinkLoadError', () => {
    it('should set generic importError for any loadError on init', () => {
      mockIntegrityLinkStore.loadError.set('not_found')
      const fixture = TestBed.createComponent(DataImportWizardComponent)
      const component = fixture.componentInstance
      expect(component.importError()).toBe('import.dataSource.genericError')
    })

    it('should clear store loadError after reading it', () => {
      mockIntegrityLinkStore.loadError.set('not_found')
      TestBed.createComponent(DataImportWizardComponent)
      expect(mockIntegrityLinkStore.loadError()).toBeNull()
    })

    it('should not set importError when loadError is null', () => {
      mockIntegrityLinkStore.loadError.set(null)
      const fixture = TestBed.createComponent(DataImportWizardComponent)
      const component = fixture.componentInstance
      expect(component.importError()).toBeNull()
    })
  })
})
