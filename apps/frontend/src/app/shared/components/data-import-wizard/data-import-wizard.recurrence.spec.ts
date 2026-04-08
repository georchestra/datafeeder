import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { provideRouter } from '@angular/router'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { DataImportWizardComponent } from './data-import-wizard.component'
import type { IntegrityLinkResponse } from '../../../core/api/models/integrity-link-response'
import { IntegrityLinkStore } from '../../../core/stores/integrity-link.store'
import { signal } from '@angular/core'

const TRANSLATIONS = {
  'import.recurrence.label': 'Recurrence',
  'recurrence.none': 'No recurrence',
  'recurrence.preset.EVERY_DAY': 'Every day',
  'recurrence.preset.EVERY_WEEK': 'Every week',
  'recurrence.preset.EVERY_MONTH': 'Every month'
}

const MOCK_PRESETS = [
  { id: 'EVERY_DAY', cron: '0 4 * * *' },
  { id: 'EVERY_WEEK', cron: '0 4 * * 1' }
]

const MOCK_INTEGRITY_LINK: IntegrityLinkResponse = {
  id: 'test-link-id',
  integrity_organization: 'org',
  integrity_owner: 'owner',
  integrity_title: 'Test Dataset',
  gn_is_published: null,
  schedule: null,
  schedule_enabled: false,
  source_import_type: 'url',
  source_file_name: null,
  source_file_type: null,
  source_url: 'https://example.com/data.csv',
  source_username: null,
  staging_table_name: 'staging_test',
  staging_retrieve_time: '0:02:00',
  created_at: null,
  data_id: null,
  final_table_name: null,
  last_retrieval_timestamp: null,
  metadata_id: null,
  access_level: null
}

describe('DataImportWizardComponent — Recurrence', () => {
  let mockIntegrityLinkStore: {
    intlinkId: ReturnType<typeof signal<string | null>>
    integrityLink: ReturnType<typeof signal<IntegrityLinkResponse | null>>
    loadError: ReturnType<typeof signal<string | null>>
    setAndLoadIntegrityLink: ReturnType<typeof vi.fn>
    clearIntegrityLink: ReturnType<typeof vi.fn>
  }
  let httpMock: HttpTestingController

  beforeEach(async () => {
    mockIntegrityLinkStore = {
      intlinkId: signal<string | null>(null),
      integrityLink: signal<IntegrityLinkResponse | null>(null),
      loadError: signal<string | null>(null),
      setAndLoadIntegrityLink: vi.fn(),
      clearIntegrityLink: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [
        DataImportWizardComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({ en: TRANSLATIONS })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore }
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

  const flushPresetsRequest = () => {
    const req = httpMock.expectOne((r) =>
      r.url.includes('/ingestion/recurrence-presets')
    )
    req.flush(MOCK_PRESETS)
  }

  it('should initialize selectedPresetId as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.selectedPresetId()).toBeNull()
  })

  it('should initialize integrityLink as null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    expect(mockIntegrityLinkStore.integrityLink()).toBeNull()
  })

  it('should return isRemoteSource false when integrityLink is null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.isRemoteSource()).toBe(false)
  })

  it('should return isRemoteSource true for url source type', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    mockIntegrityLinkStore.integrityLink.set({
      ...MOCK_INTEGRITY_LINK,
      source_import_type: 'url'
    })
    fixture.detectChanges()
    expect(component.isRemoteSource()).toBe(true)
  })

  it('should return isRemoteSource false for file source type', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    mockIntegrityLinkStore.integrityLink.set({
      ...MOCK_INTEGRITY_LINK,
      source_import_type: 'file'
    })
    fixture.detectChanges()
    expect(component.isRemoteSource()).toBe(false)
  })

  it('should return isRemoteSource true for ftp source type', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    mockIntegrityLinkStore.integrityLink.set({
      ...MOCK_INTEGRITY_LINK,
      source_import_type: 'ftp'
    })
    fixture.detectChanges()
    expect(component.isRemoteSource()).toBe(true)
  })

  it('should return isRemoteSource true for database source type', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    mockIntegrityLinkStore.integrityLink.set({
      ...MOCK_INTEGRITY_LINK,
      source_import_type: 'database'
    })
    fixture.detectChanges()
    expect(component.isRemoteSource()).toBe(true)
  })

  it('should load recurrence presets from the API on init', async () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    flushPresetsRequest()
    await fixture.whenStable()

    expect(component.recurrencePresets()).toEqual(MOCK_PRESETS)
  })

  it('should show recurrence selector in step 2 when isRemoteSource is true', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.selectedTabIndex.set(1)
    mockIntegrityLinkStore.integrityLink.set(MOCK_INTEGRITY_LINK)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-recurrence-selector')).toBeTruthy()
  })

  it('should not show recurrence selector in step 2 when source is file', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.selectedTabIndex.set(1)
    mockIntegrityLinkStore.integrityLink.set({
      ...MOCK_INTEGRITY_LINK,
      source_import_type: 'file'
    })
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-recurrence-selector')).toBeNull()
  })

  it('should not show recurrence selector in step 2 when integrityLink is null', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.selectedTabIndex.set(1)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-recurrence-selector')).toBeNull()
  })

  it('should update selectedPresetId when set', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.selectedPresetId.set('EVERY_DAY')
    fixture.detectChanges()

    expect(component.selectedPresetId()).toBe('EVERY_DAY')
  })

  it('should reset selectedPresetId to null when onConfigureDataset is called', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    component.selectedPresetId.set('EVERY_WEEK')
    component.importData.set({
      source: { type: 'url', url: 'http://example.com/data.csv' }
    } as any)
    fixture.detectChanges()

    // selectedPresetId is reset synchronously at the start of onConfigureDataset,
    // before any HTTP calls — no need to await the full import flow
    component.onConfigureDataset()

    expect(component.selectedPresetId()).toBeNull()
  })
})
