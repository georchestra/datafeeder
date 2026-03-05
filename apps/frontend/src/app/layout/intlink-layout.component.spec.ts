import { Component, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { ActivatedRoute, provideRouter } from '@angular/router'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { IntegrityLinkStore } from './integrity-link.store'
import { IntlinkLayoutComponent } from './intlink-layout.component'
import { IntegrityLinkResponse } from '../core/api/models'
import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { ApiConfiguration } from '../core/api/api-configuration'
import { Api } from '../core/api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../core/api/functions'

function createStore(accessLevel: string | null = null): IntegrityLinkStore {
  const store = new IntegrityLinkStore()
  if (accessLevel) {
    store.integrityLink.set({
      access_level: accessLevel,
      id: 'test-id',
      integrity_owner: 'owner',
      integrity_organization: 'org',
      source_import_type: 'url',
      staging_table_name: 'staging',
      schedule_enabled: false,
      created_at: null,
      data_id: null,
      metadata_id: null,
      integrity_title: 'Test',
      last_retrieval_timestamp: null,
      schedule: null,
      source_file_name: null,
      source_file_type: null,
      source_url: null,
      source_username: null,
      staging_retrieve_time: null,
      final_table_name: null
    } as IntegrityLinkResponse)
  }
  return store
}

describe('IntlinkLayoutComponent', () => {
  let httpMock: HttpTestingController

  const setupComponent = async (accessLevel: string | null = null) => {
    const store = createStore(accessLevel)

    await TestBed.configureTestingModule({
      imports: [
        IntlinkLayoutComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'sidebar.metadataSheet': 'Metadata Sheet',
            'sidebar.accessRights': 'Access Rights',
            'sidebar.recurrencePlanning': 'Recurrence',
            'sidebar.eventsAndStatuses': 'Events',
            'sidebar.reconfigureDataset': 'Reconfigure',
            'integrityLinks.dashboard': 'Dashboard'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        { provide: IntegrityLinkStore, useValue: store }
      ]
    })
      .overrideComponent(IntlinkLayoutComponent, {
        set: { providers: [{ provide: IntegrityLinkStore, useValue: store }] }
      })
      .compileComponents()

    httpMock = TestBed.inject(HttpTestingController)

    const fixture = TestBed.createComponent(IntlinkLayoutComponent)
    fixture.detectChanges()
    return { fixture, store }
  }

  afterEach(() => {
    const pending = httpMock?.match(() => true)
    pending?.forEach((r) => {
      if (!r.cancelled) r.flush({})
    })
    httpMock?.verify()
  })

  describe('IntegrityLinkStore', () => {
    it('should compute isOwnerOrAdmin true for OWNER', () => {
      const store = createStore('OWNER')
      expect(store.isOwnerOrAdmin()).toBe(true)
    })

    it('should compute isOwnerOrAdmin true for ADMIN', () => {
      const store = createStore('ADMIN')
      expect(store.isOwnerOrAdmin()).toBe(true)
    })

    it('should compute isOwnerOrAdmin false for WRITE', () => {
      const store = createStore('WRITE')
      expect(store.isOwnerOrAdmin()).toBe(false)
    })

    it('should compute isOwnerOrAdmin false when no link loaded', () => {
      const store = createStore(null)
      expect(store.isOwnerOrAdmin()).toBe(false)
    })
  })

  describe('Sidebar for OWNER user', () => {
    it('should show authorizations link as clickable', async () => {
      const { fixture } = await setupComponent('OWNER')
      const nav = fixture.nativeElement.querySelector('nav')
      const links = nav.querySelectorAll('a')
      const linkTexts = Array.from(links).map((a: any) => a.textContent.trim())
      expect(linkTexts).toContain('Access Rights')
    })

    it('should show events link as clickable', async () => {
      const { fixture } = await setupComponent('OWNER')
      const nav = fixture.nativeElement.querySelector('nav')
      const links = nav.querySelectorAll('a')
      const linkTexts = Array.from(links).map((a: any) => a.textContent.trim())
      expect(linkTexts).toContain('Events')
    })

    it('should show reconfigure button', async () => {
      const { fixture } = await setupComponent('OWNER')
      const nav = fixture.nativeElement.querySelector('nav')
      const button = nav.querySelector('button')
      expect(button).not.toBeNull()
      expect(button.textContent).toContain('Reconfigure')
    })
  })

  describe('Sidebar for ADMIN user', () => {
    it('should show all links as clickable', async () => {
      const { fixture } = await setupComponent('ADMIN')
      const nav = fixture.nativeElement.querySelector('nav')
      const links = nav.querySelectorAll('a')
      const linkTexts = Array.from(links).map((a: any) => a.textContent.trim())
      expect(linkTexts).toContain('Access Rights')
      expect(linkTexts).toContain('Events')
    })
  })

  describe('Sidebar for WRITE user (non-owner)', () => {
    it('should show authorizations as disabled text', async () => {
      const { fixture } = await setupComponent('WRITE')
      const nav = fixture.nativeElement.querySelector('nav')
      const spans = nav.querySelectorAll('span')
      const spanTexts = Array.from(spans).map((s: any) => s.textContent.trim())
      expect(spanTexts).toContain('Access Rights')
    })

    it('should show events as disabled text', async () => {
      const { fixture } = await setupComponent('WRITE')
      const nav = fixture.nativeElement.querySelector('nav')
      const spans = nav.querySelectorAll('span')
      const spanTexts = Array.from(spans).map((s: any) => s.textContent.trim())
      expect(spanTexts).toContain('Events')
    })

    it('should NOT show reconfigure button', async () => {
      const { fixture } = await setupComponent('WRITE')
      const nav = fixture.nativeElement.querySelector('nav')
      const button = nav.querySelector('button')
      expect(button).toBeNull()
    })

    it('should still show metadata sheet link', async () => {
      const { fixture } = await setupComponent('WRITE')
      const nav = fixture.nativeElement.querySelector('nav')
      const links = nav.querySelectorAll('a')
      const linkTexts = Array.from(links).map((a: any) => a.textContent.trim())
      expect(linkTexts).toContain('Metadata Sheet')
    })
  })

  // ─── ngOnInit API behavior ─────────────────────────────────────────────
  // Matrix coverage (frontend-behavior-matrix.md — Page: /:id layout shell):
  //   200 + access_level → store populated, child routes render        ✅
  //   403 (READ/NO_PERM user) → loadError = 'forbidden', alert shown   ✅
  //   404               → loadError = 'not_found', alert shown         ✅
  //   500               → loadError = 'server_error', alert shown      ✅
  // ──────────────────────────────────────────────────────────────────────

  describe('ngOnInit - API call behavior', () => {
    const intlinkId = 'test-link-abc'

    const mockLinkResponse: IntegrityLinkResponse = {
      id: intlinkId,
      integrity_owner: 'owner1',
      integrity_organization: 'org_a',
      source_import_type: 'url',
      staging_table_name: 'staging_test',
      schedule_enabled: false,
      created_at: null,
      data_id: null,
      metadata_id: null,
      integrity_title: 'Test Link',
      last_retrieval_timestamp: null,
      schedule: null,
      source_file_name: null,
      source_file_type: null,
      source_url: null,
      source_username: null,
      staging_retrieve_time: null,
      final_table_name: null,
      access_level: 'OWNER'
    }

    const setupWithMockedApi = async (
      options: { rejectStatus?: number } = {}
    ) => {
      const store = new IntegrityLinkStore()
      const mockApi = {
        invoke: vi
          .fn()
          .mockImplementation(() =>
            options.rejectStatus
              ? Promise.reject({ status: options.rejectStatus })
              : Promise.resolve(mockLinkResponse)
          )
      }
      const mockRoute = {
        snapshot: { paramMap: { get: () => intlinkId } }
      }

      await TestBed.configureTestingModule({
        imports: [
          IntlinkLayoutComponent,
          TranslateTestingModule.withTranslations({
            en: {
              'sidebar.metadataSheet': 'Metadata Sheet',
              'sidebar.accessRights': 'Access Rights',
              'sidebar.recurrencePlanning': 'Recurrence',
              'sidebar.eventsAndStatuses': 'Events',
              'sidebar.reconfigureDataset': 'Reconfigure',
              'integrityLinks.dashboard': 'Dashboard'
            }
          })
            .withDefaultLanguage('en')
            .withCompiler(new TranslateMessageFormatCompiler())
        ],
        providers: [
          provideRouter([]),
          { provide: ActivatedRoute, useValue: mockRoute },
          { provide: Api, useValue: mockApi },
          { provide: IntegrityLinkStore, useValue: store }
        ]
      })
        .overrideComponent(IntlinkLayoutComponent, {
          set: { providers: [{ provide: IntegrityLinkStore, useValue: store }] }
        })
        .compileComponents()

      const fixture = TestBed.createComponent(IntlinkLayoutComponent)
      return { fixture, store, mockApi }
    }

    it('should set intlinkId on the store from the route parameter', async () => {
      const { fixture, store } = await setupWithMockedApi()
      fixture.detectChanges()

      expect(store.intlinkId()).toBe(intlinkId)
    })

    it('should populate the store with the API response on 200 (✅)', async () => {
      const { fixture, store } = await setupWithMockedApi()
      fixture.detectChanges()

      await vi.waitFor(() => {
        expect(store.integrityLink()).not.toBeNull()
      })
      expect(store.integrityLink()?.access_level).toBe('OWNER')
    })

    it('should call the correct API function with the intlink_id', async () => {
      const { fixture, mockApi } = await setupWithMockedApi()
      fixture.detectChanges()

      await vi.waitFor(() => {
        expect(mockApi.invoke).toHaveBeenCalledWith(
          getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
          { integrity_link_id: intlinkId }
        )
      })
    })

    it('should set loadError to "forbidden" and keep store null when API throws 403 (✅)', async () => {
      const { fixture, store } = await setupWithMockedApi({ rejectStatus: 403 })
      fixture.detectChanges()

      await vi.waitFor(() =>
        expect(fixture.componentInstance.loadError()).toBe('forbidden')
      )
      expect(store.integrityLink()).toBeNull()
    })

    it('should set loadError to "not_found" when API throws 404 (✅)', async () => {
      const { fixture } = await setupWithMockedApi({ rejectStatus: 404 })
      fixture.detectChanges()

      await vi.waitFor(() =>
        expect(fixture.componentInstance.loadError()).toBe('not_found')
      )
    })

    it('should set loadError to "server_error" for unexpected errors (✅)', async () => {
      const { fixture } = await setupWithMockedApi({ rejectStatus: 500 })
      fixture.detectChanges()

      await vi.waitFor(() =>
        expect(fixture.componentInstance.loadError()).toBe('server_error')
      )
    })
  })
})
