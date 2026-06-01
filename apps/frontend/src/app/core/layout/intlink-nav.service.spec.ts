import { computed, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideRouter } from '@angular/router'
import { Router } from '@angular/router'
import { of } from 'rxjs'
import { MatDialog } from '@angular/material/dialog'
import { TranslateService } from '@ngx-translate/core'
import { IntlinkNavService } from './intlink-nav.service'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { SettingsService } from '../settings/settings.service'
import { Api } from '../api/api'
import { IntegrityLinkResponse } from '../api/models'

function createStore(
  opts: {
    accessLevel?: string
    isEmpty?: boolean
    isLocal?: boolean
    scheduleEnabled?: boolean
    intlinkId?: string | null
  } = {}
) {
  const {
    accessLevel = 'OWNER',
    isEmpty = false,
    isLocal = false,
    scheduleEnabled = false,
    intlinkId = 'intlink-1'
  } = opts

  const integrityLink = signal<IntegrityLinkResponse | null>({
    id: 'intlink-1',
    access_level: accessLevel,
    source_import_type: isEmpty ? 'empty' : isLocal ? 'file' : 'url',
    schedule_enabled: scheduleEnabled,
    integrity_title: 'Test',
    integrity_owner: 'owner',
    integrity_organization: 'org',
    staging_table_name: 'staging',
    created_at: null,
    data_id: null,
    metadata_id: 'meta-abc',
    last_retrieval_timestamp: null,
    schedule: null,
    source_file_name: null,
    source_file_type: null,
    source_url: null,
    source_username: null,
    staging_retrieve_time: null,
    final_table_name: null
  } as IntegrityLinkResponse)

  const accessLevelComputed = computed(
    () => integrityLink()?.access_level ?? null
  )
  return {
    integrityLink,
    intlinkId: signal<string | null>(intlinkId),
    isOwnerOrAdmin: computed(() => {
      const l = accessLevelComputed()
      return l === 'OWNER' || l === 'ADMIN'
    }),
    isEmptyDataset: computed(
      () => integrityLink()?.source_import_type === 'empty'
    ),
    isRemoteDataset: computed(() => {
      const t = integrityLink()?.source_import_type
      return t != null && t !== 'file' && t !== 'empty'
    })
  } as unknown as IntegrityLinkStore
}

function setup(storeOpts: Parameters<typeof createStore>[0] = {}) {
  const store = createStore(storeOpts)

  const mockSettings = {
    getSetting: vi.fn().mockReturnValue(undefined)
  }

  const mockApi = {
    invoke: vi.fn().mockResolvedValue({ dag_runs: [] })
  }

  const mockDialog = {
    open: vi.fn()
  }

  const mockTranslate = {
    instant: vi.fn().mockImplementation((key: string) => key)
  }

  TestBed.configureTestingModule({
    providers: [
      IntlinkNavService,
      provideRouter([]),
      { provide: IntegrityLinkStore, useValue: store },
      { provide: SettingsService, useValue: mockSettings },
      { provide: Api, useValue: mockApi },
      { provide: MatDialog, useValue: mockDialog },
      { provide: TranslateService, useValue: mockTranslate }
    ]
  })

  const service = TestBed.inject(IntlinkNavService)
  const router = TestBed.inject(Router)

  return {
    service,
    store,
    mockSettings,
    mockApi,
    mockDialog,
    mockTranslate,
    router
  }
}

describe('IntlinkNavService', () => {
  describe('accessibleRoutes', () => {
    it('should include only edit for WRITE user', () => {
      const { service } = setup({ accessLevel: 'WRITE' })
      expect(service.accessibleRoutes()).toEqual(['edit'])
    })

    it('should include edit and authorizations for OWNER with no data (empty dataset)', () => {
      const { service } = setup({ accessLevel: 'OWNER', isEmpty: true })
      expect(service.accessibleRoutes()).toEqual(['edit', 'authorizations'])
    })

    it('should include edit and authorizations for OWNER with a local (file) dataset', () => {
      const { service } = setup({ accessLevel: 'OWNER', isLocal: true })
      expect(service.accessibleRoutes()).toEqual(['edit', 'authorizations'])
    })

    it('should include recurrence for OWNER with a remote dataset', () => {
      const { service } = setup({ accessLevel: 'OWNER', isEmpty: false })
      expect(service.accessibleRoutes()).toEqual([
        'edit',
        'recurrence',
        'authorizations'
      ])
    })

    it('should include recurrence for ADMIN with a remote dataset', () => {
      const { service } = setup({ accessLevel: 'ADMIN', isEmpty: false })
      expect(service.accessibleRoutes()).toEqual([
        'edit',
        'recurrence',
        'authorizations'
      ])
    })
  })

  describe('prevRoute', () => {
    it('should return null for edit (first route)', () => {
      const { service } = setup()
      expect(service.prevRoute('edit')).toBeNull()
    })

    it('should return edit before recurrence', () => {
      const { service } = setup()
      expect(service.prevRoute('recurrence')).toBe('edit')
    })

    it('should return recurrence before authorizations for a remote dataset', () => {
      const { service } = setup()
      expect(service.prevRoute('authorizations')).toBe('recurrence')
    })

    it('should return edit before authorizations when recurrence is not accessible (local dataset)', () => {
      const { service } = setup({ isLocal: true })
      expect(service.prevRoute('authorizations')).toBe('edit')
    })
  })

  describe('nextRoute', () => {
    it('should return null for the last accessible route', () => {
      const { service } = setup()
      expect(service.nextRoute('authorizations')).toBeNull()
    })

    it('should return recurrence after edit for OWNER with a remote dataset', () => {
      const { service } = setup()
      expect(service.nextRoute('edit')).toBe('recurrence')
    })

    it('should return authorizations after edit for OWNER with a local dataset', () => {
      const { service } = setup({ isLocal: true })
      expect(service.nextRoute('edit')).toBe('authorizations')
    })

    it('should return null after edit for WRITE user', () => {
      const { service } = setup({ accessLevel: 'WRITE' })
      expect(service.nextRoute('edit')).toBeNull()
    })

    it('should return authorizations after recurrence', () => {
      const { service } = setup()
      expect(service.nextRoute('recurrence')).toBe('authorizations')
    })
  })

  describe('nextRouteLabel', () => {
    it('should return footer.next.recurrence for recurrence', () => {
      const { service } = setup()
      expect(service.nextRouteLabel('recurrence')).toBe(
        'footer.next.recurrence'
      )
    })

    it('should return footer.next.authorizations for authorizations', () => {
      const { service } = setup()
      expect(service.nextRouteLabel('authorizations')).toBe(
        'footer.next.authorizations'
      )
    })
  })

  describe('catalogueUrl', () => {
    it('should return null when no template is configured', () => {
      const { service } = setup()
      expect(service.catalogueUrl('meta-abc')).toBeNull()
    })

    it('should return null when metadataId is null', () => {
      const { service, mockSettings } = setup()
      mockSettings.getSetting.mockReturnValue(
        'https://catalogue.example.com/record/{metadata_id}'
      )
      expect(service.catalogueUrl(null)).toBeNull()
    })

    it('should interpolate metadata_id into the template', () => {
      const { service, mockSettings } = setup()
      mockSettings.getSetting.mockReturnValue(
        'https://catalogue.example.com/record/{metadata_id}'
      )
      expect(service.catalogueUrl('meta-abc')).toBe(
        'https://catalogue.example.com/record/meta-abc'
      )
    })
  })

  describe('navigate', () => {
    it('should navigate to /:intlinkId/:route', async () => {
      const { service, router } = setup()
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      await service.navigate('intlink-1', 'events')
      expect(spy).toHaveBeenCalledWith(['/', 'intlink-1', 'events'])
    })
  })

  describe('reconfigure', () => {
    it('should navigate to /import/:intlinkId when schedule is disabled', async () => {
      const { service, router } = setup({ scheduleEnabled: false })
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      await service.reconfigure()
      expect(spy).toHaveBeenCalledWith(['/import', 'intlink-1'])
    })

    it('should do nothing when store has no intlink loaded', async () => {
      const { service, router, store } = setup()
      store.integrityLink.set(null)
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      await service.reconfigure()
      expect(spy).not.toHaveBeenCalled()
    })

    it('should open a confirmation dialog when schedule is enabled', async () => {
      const { service, mockApi, mockDialog } = setup({ scheduleEnabled: true })
      mockApi.invoke.mockResolvedValue({ dag_runs: [] })
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) })
      await service.reconfigure()
      expect(mockDialog.open).toHaveBeenCalled()
    })

    it('should not navigate when user cancels the dialog', async () => {
      const { service, router, mockApi, mockDialog } = setup({
        scheduleEnabled: true
      })
      mockApi.invoke.mockResolvedValue({ dag_runs: [] })
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) })
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      await service.reconfigure()
      expect(spy).not.toHaveBeenCalled()
    })

    it('should delete the schedule and navigate when user confirms', async () => {
      const { service, router, mockApi, mockDialog } = setup({
        scheduleEnabled: true
      })
      mockApi.invoke
        .mockResolvedValueOnce({ dag_runs: [] }) // getDagRunByIntlink
        .mockResolvedValueOnce({}) // deleteSchedule
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) })
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
      await service.reconfigure()
      expect(mockApi.invoke).toHaveBeenCalledTimes(2)
      expect(spy).toHaveBeenCalledWith(['/import', 'intlink-1'])
    })

    it('should use the active run warning message key when a run is active', async () => {
      const { service, mockApi, mockDialog, mockTranslate } = setup({
        scheduleEnabled: true
      })
      mockApi.invoke.mockResolvedValue({
        dag_runs: [{ state: 'running' }]
      })
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) })
      await service.reconfigure()
      expect(mockTranslate.instant).toHaveBeenCalledWith(
        'sidebar.reconfigureDataset.warningActiveRun'
      )
    })
  })
})
