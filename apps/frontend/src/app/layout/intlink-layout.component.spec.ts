import { computed, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideRouter } from '@angular/router'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { IntlinkLayoutComponent } from './intlink-layout.component'
import { IntegrityLinkResponse } from '../core/api/models'
import { of, throwError } from 'rxjs'
import { EditorFacade, RecordsRepositoryInterface } from 'geonetwork-ui'

/**
 * Creates a lightweight store mock using Angular signals/computed.
 * Avoids instantiating the real IntegrityLinkStore (which requires an
 * injection context for its internal Api dependency).
 */
function createStore(accessLevel: string | null = null): IntegrityLinkStore {
  const integrityLink = signal<IntegrityLinkResponse | null>(
    accessLevel !== null
      ? ({
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
      : null
  )
  const accessLevelComputed = computed(
    () => integrityLink()?.access_level ?? null
  )
  return {
    integrityLink,
    intlinkId: signal<string | null>(null),
    loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(null),
    accessLevel: accessLevelComputed,
    isOwnerOrAdmin: computed(() => {
      const level = accessLevelComputed()
      return level === 'OWNER' || level === 'ADMIN'
    })
  } as unknown as IntegrityLinkStore
}

describe('IntlinkLayoutComponent', () => {
  const setupComponent = async (accessLevel: string | null = null) => {
    const store = createStore(accessLevel)

    const mockEditor = {
      record$: of({ id: 'test-record' }),
      recordSource$: of('xml-source')
    }

    const mockRepo = {
      saveRecord: vi.fn().mockReturnValue(of({}))
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
        { provide: IntegrityLinkStore, useValue: store },
        { provide: EditorFacade, useValue: mockEditor },
        { provide: RecordsRepositoryInterface, useValue: mockRepo }
      ]
    })
      .overrideComponent(IntlinkLayoutComponent, {
        set: { providers: [{ provide: IntegrityLinkStore, useValue: store }] }
      })
      .compileComponents()

    const fixture = TestBed.createComponent(IntlinkLayoutComponent)
    fixture.detectChanges()
    return { fixture, store }
  }

  describe('isOwnerOrAdmin computed logic', () => {
    it('should return true for OWNER', () => {
      const store = createStore('OWNER')
      expect(store.isOwnerOrAdmin()).toBe(true)
    })

    it('should return true for ADMIN', () => {
      const store = createStore('ADMIN')
      expect(store.isOwnerOrAdmin()).toBe(true)
    })

    it('should return false for WRITE', () => {
      const store = createStore('WRITE')
      expect(store.isOwnerOrAdmin()).toBe(false)
    })

    it('should return false when no link is loaded', () => {
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

  // ─── Error display behavior ───────────────────────────────────────────
  // Matrix coverage (frontend-behavior-matrix.md — Page: /:id layout shell):
  //   loadError = null         → router-outlet rendered, no alert       ✅
  //   loadError = 'forbidden'  → error alert shown, no router-outlet    ✅
  //   loadError = 'not_found'  → error alert shown                      ✅
  //   loadError = 'server_error' → error alert shown                    ✅
  // ──────────────────────────────────────────────────────────────────────

  describe('Error display behavior', () => {
    it('should render router-outlet when loadError is null (✅)', async () => {
      const { fixture } = await setupComponent('OWNER')
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('router-outlet')).not.toBeNull()
      expect(content.querySelector('app-ui-alert-box')).toBeNull()
    })

    it('should show error alert and hide router-outlet when loadError is "forbidden" (✅)', async () => {
      const { fixture, store } = await setupComponent('OWNER')
      store.loadError.set('forbidden')
      fixture.detectChanges()
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('app-ui-alert-box')).not.toBeNull()
      expect(content.querySelector('router-outlet')).toBeNull()
    })

    it('should show error alert when loadError is "not_found" (✅)', async () => {
      const { fixture, store } = await setupComponent(null)
      store.loadError.set('not_found')
      fixture.detectChanges()
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('app-ui-alert-box')).not.toBeNull()
    })

    it('should show error alert when loadError is "server_error" (✅)', async () => {
      const { fixture, store } = await setupComponent(null)
      store.loadError.set('server_error')
      fixture.detectChanges()
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('app-ui-alert-box')).not.toBeNull()
    })
  })

  describe('Save Edits Behavior', () => {
    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('should call saveRecord with correct parameters', async () => {
      const { fixture, store } = await setupComponent('OWNER')
      const repo = TestBed.inject(RecordsRepositoryInterface)

      fixture.componentInstance.saveEdits()

      expect(repo.saveRecord).toHaveBeenCalledWith(
        { id: 'test-record' },
        'xml-source',
        false
      )
    })

    it('should log success message on successful save', async () => {
      const { fixture } = await setupComponent('OWNER')
      const logSpy = vi.spyOn(console, 'log')

      fixture.componentInstance.saveEdits()

      expect(logSpy).toHaveBeenCalledWith('Edits saved successfully')
    })

    it('should log error message when save fails', async () => {
      const { fixture } = await setupComponent('OWNER')
      const repo = TestBed.inject(RecordsRepositoryInterface)
      const logSpy = vi.spyOn(console, 'log')

      vi.mocked(repo.saveRecord).mockReturnValueOnce(
        throwError(() => new Error('API Error'))
      )

      fixture.componentInstance.saveEdits()

      expect(logSpy).toHaveBeenCalledWith('Failed to save edits')
    })
  })
})
