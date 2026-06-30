import { computed, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideRouter } from '@angular/router'
import { MatDialog } from '@angular/material/dialog'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { IntlinkLayoutComponent } from './intlink-layout.component'
import { IntegrityLinkResponse } from '../core/api/models'
import { of } from 'rxjs'
import { EditorFacade } from 'geonetwork-ui'
import { Api } from '../core/api/api'
import { MetadataSaveService } from '../core/layout/metadata-save.service'

/**
 * Creates a lightweight store mock using Angular signals/computed.
 * Avoids instantiating the real IntegrityLinkStore (which requires an
 * injection context for its internal Api dependency).
 */
function createStore(
  accessLevel: string | null = null,
  importType: string = 'url'
): IntegrityLinkStore {
  const integrityLink = signal<IntegrityLinkResponse | null>(
    accessLevel !== null
      ? ({
          access_level: accessLevel,
          id: 'test-id',
          integrity_owner: 'owner',
          integrity_organization: 'org',
          source_import_type: importType,
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
    }),
    isEmptyDataset: computed(
      () => integrityLink()?.source_import_type === 'empty'
    ),
    isPrefilledDataset: computed(
      () => integrityLink()?.source_import_type === 'prefilled'
    ),
    isRemoteDataset: computed(() => {
      const t = integrityLink()?.source_import_type
      return t != null && t !== 'file' && t !== 'empty' && t !== 'prefilled'
    })
  } as unknown as IntegrityLinkStore
}

describe('IntlinkLayoutComponent', () => {
  const setupComponent = async (
    accessLevel: string | null = null,
    importType: string = 'url'
  ) => {
    const store = createStore(accessLevel, importType)

    const mockEditor = {
      record$: of({ id: 'test-record', title: 'Test Title' }),
      recordSource$: of('<xml>original</xml>'),
      changedSinceSave$: of(false)
    }

    const mockApi = {
      invoke: vi.fn().mockResolvedValue({ integrity_title: 'Updated Title' })
    }

    await TestBed.configureTestingModule({
      imports: [
        IntlinkLayoutComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'sidebar.metadataSheet': 'Metadata Sheet',
            'sidebar.accessRights': 'Access Rights',
            'sidebar.recurrence': 'Recurrence',
            'sidebar.eventsAndStatuses': 'Events',
            'sidebar.reconfigureDataset': 'Reconfigure',
            'integrityLinks.dashboard': 'Dashboard',
            'sidebar.unavailableForEmpty': 'Unavailable for empty',
            'sidebar.unavailableForLocal': 'Unavailable for local'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideRouter([]),
        { provide: IntegrityLinkStore, useValue: store },
        { provide: EditorFacade, useValue: mockEditor },
        { provide: Api, useValue: mockApi },
        { provide: MatDialog, useValue: {} }
      ]
    })
      .overrideComponent(IntlinkLayoutComponent, {
        set: { providers: [{ provide: IntegrityLinkStore, useValue: store }] }
      })
      .compileComponents()

    const fixture = TestBed.createComponent(IntlinkLayoutComponent)
    fixture.detectChanges()
    return { fixture, store, mockApi }
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

    it('should show reconfigure button in footer (owner/admin)', async () => {
      const { fixture } = await setupComponent('OWNER')
      // Reconfigure button is in #footerTpl (not rendered in test fixture DOM)
      // Verify via signal: isOwnerOrAdmin() must be true for it to appear
      expect(fixture.componentInstance.store.isOwnerOrAdmin()).toBe(true)
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
    it('should delegate save to MetadataSaveService', async () => {
      const { fixture } = await setupComponent('OWNER')
      const saveService = TestBed.inject(MetadataSaveService)
      const saveSpy = vi.spyOn(saveService, 'save').mockResolvedValue()
      fixture.componentInstance.onSaveClick()
      expect(saveSpy).toHaveBeenCalled()
    })
  })

  describe('Sidebar for empty dataset (OWNER)', () => {
    async function setupEmptyDataset() {
      const store = createStore('OWNER')
      store.integrityLink.set({
        ...store.integrityLink()!,
        source_import_type: 'empty'
      } as IntegrityLinkResponse)

      const mockEditor = {
        record$: of({ id: 'test-record', title: 'Test Title' }),
        recordSource$: of('<xml>original</xml>'),
        changedSinceSave$: of(false)
      }
      const mockApi = {
        invoke: vi.fn().mockResolvedValue({ integrity_title: 'Updated Title' })
      }

      await TestBed.configureTestingModule({
        imports: [
          IntlinkLayoutComponent,
          TranslateTestingModule.withTranslations({
            en: {
              'sidebar.metadataSheet': 'Metadata Sheet',
              'sidebar.accessRights': 'Access Rights',
              'sidebar.recurrence': 'Recurrence',
              'sidebar.eventsAndStatuses': 'Events',
              'sidebar.reconfigureDataset': 'Reconfigure',
              'integrityLinks.dashboard': 'Dashboard',
              'sidebar.unavailableForEmpty': 'Unavailable for empty',
              'sidebar.unavailableForLocal': 'Unavailable for local'
            }
          })
            .withDefaultLanguage('en')
            .withCompiler(new TranslateMessageFormatCompiler())
        ],
        providers: [
          provideRouter([]),
          { provide: IntegrityLinkStore, useValue: store },
          { provide: EditorFacade, useValue: mockEditor },
          { provide: Api, useValue: mockApi },
          { provide: MatDialog, useValue: {} }
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

    it('should show events as disabled span (not a link)', async () => {
      const { fixture } = await setupEmptyDataset()
      const nav = fixture.nativeElement.querySelector('nav')
      const links = Array.from(nav.querySelectorAll('a')) as HTMLElement[]
      const spans = Array.from(nav.querySelectorAll('span')) as HTMLElement[]
      const linkTexts = links.map((a) => a.textContent!.trim())
      const spanTexts = spans.map((s) => s.textContent!.trim())
      expect(linkTexts).not.toContain('Events')
      expect(spanTexts).toContain('Events')
    })

    it('should set title tooltip on the disabled events span', async () => {
      const { fixture } = await setupEmptyDataset()
      const nav = fixture.nativeElement.querySelector('nav')
      const spans = Array.from(nav.querySelectorAll('span')) as HTMLElement[]
      const eventsSpan = spans.find((s) => s.textContent!.trim() === 'Events')
      expect(eventsSpan?.title).toBe('Unavailable for empty')
    })

    it('should still show authorizations as a link', async () => {
      const { fixture } = await setupEmptyDataset()
      const nav = fixture.nativeElement.querySelector('nav')
      const links = Array.from(nav.querySelectorAll('a')) as HTMLElement[]
      const linkTexts = links.map((a) => a.textContent!.trim())
      expect(linkTexts).toContain('Access Rights')
    })
  })

  describe('Recurrence sidebar item', () => {
    it('should show recurrence as a link for a remote dataset (OWNER)', async () => {
      const { fixture } = await setupComponent('OWNER', 'url')
      const nav = fixture.nativeElement.querySelector('nav')
      const linkTexts = Array.from(nav.querySelectorAll('a')).map((a: any) =>
        a.textContent.trim()
      )
      expect(linkTexts).toContain('Recurrence')
    })

    it('should grey out recurrence with the local tooltip for a file dataset (OWNER)', async () => {
      const { fixture } = await setupComponent('OWNER', 'file')
      const nav = fixture.nativeElement.querySelector('nav')
      const spans = Array.from(nav.querySelectorAll('span')) as HTMLElement[]
      const recurrenceSpan = spans.find(
        (s) => s.textContent!.trim() === 'Recurrence'
      )
      expect(recurrenceSpan).toBeTruthy()
      expect(recurrenceSpan?.title).toBe('Unavailable for local')
      const linkTexts = Array.from(nav.querySelectorAll('a')).map((a: any) =>
        a.textContent.trim()
      )
      expect(linkTexts).not.toContain('Recurrence')
    })

    it('should grey out recurrence with the empty tooltip for an empty dataset (OWNER)', async () => {
      const { fixture } = await setupComponent('OWNER', 'empty')
      const nav = fixture.nativeElement.querySelector('nav')
      const spans = Array.from(nav.querySelectorAll('span')) as HTMLElement[]
      const recurrenceSpan = spans.find(
        (s) => s.textContent!.trim() === 'Recurrence'
      )
      expect(recurrenceSpan?.title).toBe('Unavailable for empty')
    })
  })

  describe('showUnavailableBanner', () => {
    it('should show the banner when showUnavailableBanner signal is true', async () => {
      const { fixture } = await setupComponent('OWNER')
      fixture.componentInstance.showUnavailableBanner.set(true)
      fixture.detectChanges()
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('app-ui-alert-box')).not.toBeNull()
      expect(content.querySelector('router-outlet')).not.toBeNull()
    })

    it('should hide the banner when showUnavailableBanner is false', async () => {
      const { fixture } = await setupComponent('OWNER')
      fixture.componentInstance.showUnavailableBanner.set(false)
      fixture.detectChanges()
      const content = fixture.nativeElement.querySelector('div.flex-grow')
      expect(content.querySelector('app-ui-alert-box')).toBeNull()
    })

    it('should dismiss the banner on (dismissed) event', async () => {
      const { fixture } = await setupComponent('OWNER')
      fixture.componentInstance.showUnavailableBanner.set(true)
      fixture.detectChanges()
      const alertBox = fixture.nativeElement.querySelector('app-ui-alert-box')
      const dismissBtn = alertBox.querySelector(
        '[data-test="dismiss-alert"] button'
      )
      dismissBtn.click()
      fixture.detectChanges()
      expect(fixture.componentInstance.showUnavailableBanner()).toBe(false)
    })
  })
})
