import { TestBed } from '@angular/core/testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
  listGroupsDataGroupsGet,
  listGroupsMetadataGroupsGet,
  listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
  togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut,
  upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
} from '../../core/api/functions'
import { GroupItem, IntegrityLinkRule } from '../../core/api/models'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { AuthorizationsComponent } from './authorizations.component'

describe('AuthorizationsComponent', () => {
  const intlinkId = 'link-42'

  const mockGeonetworkGroups: GroupItem[] = [
    { id: 'org-1', label: 'Organization A' }
  ]

  const mockGeoserverGroups: GroupItem[] = [
    { id: 'role-1', label: 'ROLE_ADMIN' },
    { id: 'role-2', label: 'ROLE_EDITOR' }
  ]

  const mockRules: IntegrityLinkRule[] = [
    {
      id: 10,
      integrity_link_id: intlinkId,
      group_or_role: 'org-1',
      rule_type: 'METADATA',
      rule_value: 'READ'
    },
    {
      id: 11,
      integrity_link_id: intlinkId,
      group_or_role: 'role-1',
      rule_type: 'DATA',
      rule_value: 'WRITE'
    }
  ]

  let apiInvokeSpy: ReturnType<typeof vi.fn>
  let store: IntegrityLinkStore

  const createComponent = () => {
    const fixture = TestBed.createComponent(AuthorizationsComponent)
    fixture.detectChanges()
    return { fixture, component: fixture.componentInstance }
  }

  beforeEach(async () => {
    apiInvokeSpy = vi.fn().mockImplementation((fn: unknown) => {
      if (fn === listGroupsMetadataGroupsGet)
        return Promise.resolve(mockGeonetworkGroups)
      if (fn === listGroupsDataGroupsGet)
        return Promise.resolve(mockGeoserverGroups)
      if (
        fn ===
        listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
      )
        return Promise.resolve(mockRules)
      return Promise.resolve(null)
    })

    await TestBed.configureTestingModule({
      imports: [
        AuthorizationsComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'authorizations.title': 'Authorizations',
            'authorizations.geonetwork': 'GeoNetwork authorizations',
            'authorizations.geonetwork.search':
              'Search for an organization listed on GeoNetwork',
            'authorizations.geoserver': 'GeoServer authorizations',
            'authorizations.geoserver.search':
              'Search for a role listed on GeoServer',
            'authorizations.ruleValue.none': 'None',
            'authorizations.ruleValue.public': 'Public',
            'authorizations.ruleValue.read': 'Read',
            'authorizations.ruleValue.write': 'Write',
            'authorizations.geonetwork.publishError.title': 'Publication Error',
            'authorizations.geonetwork.publishError.defaultMessage':
              'An error occurred during publication',
            'i18nerror.publish.geonetwork':
              'Error publishing metadata to GeoNetwork'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        IntegrityLinkStore,
        {
          provide: Api,
          useValue: { invoke: apiInvokeSpy }
        }
      ]
    }).compileComponents()

    store = TestBed.inject(IntegrityLinkStore)
    store.intlinkId.set(intlinkId)
    store.integrityLink.set({
      integrity_link_id: intlinkId,
      integrity_title: 'Test Link'
    } as any)
  })

  it('should load geoserver groups on init', async () => {
    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.geoserverGroups()).toEqual(mockGeoserverGroups)
    })
  })

  it('should compute dataRules from rules signal', async () => {
    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.dataRules().length).toBe(1)
    })
    expect(component.dataRules()[0].rule_type).toBe('DATA')
    expect(component.dataRules()[0].group_or_role).toBe('role-1')
  })

  it('should compute metadataRules from rules signal', async () => {
    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.metadataRules().length).toBe(1)
    })
    expect(component.metadataRules()[0].rule_type).toBe('METADATA')
    expect(component.metadataRules()[0].group_or_role).toBe('org-1')
  })

  it('should call upsert with DATA rule_type on data rule change', async () => {
    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.rules().length).toBe(2)
    })

    await component.onDataRuleChange({
      group: { id: 'role-2', label: 'ROLE_EDITOR' },
      value: 'READ'
    })

    expect(apiInvokeSpy).toHaveBeenCalledWith(
      upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut,
      {
        integrity_link_id: intlinkId,
        body: {
          group_or_role: 'role-2',
          rule_type: 'DATA',
          rule_value: 'READ'
        }
      }
    )
  })

  it('should call delete on data rule change with NONE', async () => {
    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.rules().length).toBe(2)
    })

    await component.onDataRuleChange({
      group: { id: 'role-1', label: 'ROLE_ADMIN' },
      value: 'NONE'
    })

    expect(apiInvokeSpy).toHaveBeenCalledWith(
      deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
      {
        integrity_link_id: intlinkId,
        rule_id: 11
      }
    )
  })

  it('should find correct existing rule by type when handling data rule change', async () => {
    const sharedId = 'shared-id'
    const rulesWithCollision: IntegrityLinkRule[] = [
      {
        id: 20,
        integrity_link_id: intlinkId,
        group_or_role: sharedId,
        rule_type: 'METADATA',
        rule_value: 'READ'
      },
      {
        id: 21,
        integrity_link_id: intlinkId,
        group_or_role: sharedId,
        rule_type: 'DATA',
        rule_value: 'WRITE'
      }
    ]

    apiInvokeSpy.mockImplementation((fn: unknown) => {
      if (
        fn ===
        listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
      )
        return Promise.resolve(rulesWithCollision)
      if (fn === listGroupsMetadataGroupsGet)
        return Promise.resolve(mockGeonetworkGroups)
      if (fn === listGroupsDataGroupsGet)
        return Promise.resolve(mockGeoserverGroups)
      return Promise.resolve(null)
    })

    const { component } = createComponent()
    await vi.waitFor(() => {
      expect(component.rules().length).toBe(2)
    })

    await component.onDataRuleChange({
      group: { id: sharedId, label: 'Shared' },
      value: 'NONE'
    })

    expect(apiInvokeSpy).toHaveBeenCalledWith(
      deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
      {
        integrity_link_id: intlinkId,
        rule_id: 21
      }
    )
  })

  // ─── Error handling ──────────────────────────────────────────────────────
  // Matrix coverage (frontend-behavior-matrix.md — Page: /:id/authorizations):
  //   403 on GET rules → loadError signal set, rules stays empty       ✅
  //   403 on PUT/DELETE rule → mutationError signal set                ✅

  describe('Error handling', () => {
    it('should set loadError and leave rules empty when listRules API returns 403 (✅)', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.reject({ status: 403, message: 'Forbidden' })
        if (fn === listGroupsMetadataGroupsGet) return Promise.resolve([])
        if (fn === listGroupsDataGroupsGet) return Promise.resolve([])
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await vi.waitFor(() => expect(component.loadError()).not.toBeNull())
      expect(component.rules()).toEqual([])
    })

    it('should set mutationError and leave rules unchanged when upsert returns 403 (✅)', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
        )
          return Promise.reject({ status: 403, message: 'Forbidden' })
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await vi.waitFor(() => expect(component.rules().length).toBe(2))

      await component.onMetadataRuleChange({
        group: { id: 'org-1', label: 'Organization A' },
        value: 'WRITE'
      })

      expect(component.mutationError()).not.toBeNull()
      // rules unchanged — loadRules was not called after the failed upsert
      expect(component.rules().length).toBe(2)
    })

    it('should clear loadError when subsequent load succeeds', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.reject({ status: 403 })
        if (fn === listGroupsMetadataGroupsGet) return Promise.resolve([])
        if (fn === listGroupsDataGroupsGet) return Promise.resolve([])
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await vi.waitFor(() => expect(component.loadError()).not.toBeNull())

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        return Promise.resolve([])
      })
      ;(component as any).loadRules(intlinkId)

      await vi.waitFor(() => expect(component.loadError()).toBeNull())
      expect(component.rules().length).toBe(2)
    })
  })

  describe('onTogglePublishGn', () => {
    it('should call toggle publish API with publish=true and update signals on success', async () => {
      const updatedLink = {
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: true
      } as any

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGn(true)

      expect(apiInvokeSpy).toHaveBeenCalledWith(
        togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut,
        { integrity_link_id: intlinkId, publish: true }
      )
      expect(component.isPublishedGn()).toBe(true)
      expect(component.isPublishing()).toBe(false)
      expect(component.publishError()).toBeNull()
    })

    it('should call toggle publish API with publish=false and update signals on success', async () => {
      store.integrityLink.set({
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: true
      } as any)

      const updatedLink = {
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: false
      } as any

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGn(false)

      expect(component.isPublishedGn()).toBe(false)
      expect(component.publishError()).toBeNull()
    })

    it('should set publishError with default message on generic error', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return Promise.reject(new Error('Network error'))
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGn(true)

      expect(component.publishError()).toBe('Network error')
      expect(component.isPublishing()).toBe(false)
    })

    it('should set publishError with translated i18n key from backend detail', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return Promise.reject({
            error: { detail: 'i18nerror.publish.geonetwork' }
          })
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGn(true)

      expect(component.publishError()).toBe(
        'Error publishing metadata to GeoNetwork'
      )
      expect(component.isPublishing()).toBe(false)
    })

    it('should clear publishError at start of a new toggle call', async () => {
      const updatedLink = {
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: true
      } as any

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      component.publishError.set('Previous error')

      await component.onTogglePublishGn(true)

      expect(component.publishError()).toBeNull()
    })

    it('should optimistically update isPublishedGn before API resolves', async () => {
      let resolveToggle!: (v: any) => void
      const togglePromise = new Promise((resolve) => {
        resolveToggle = resolve
      })

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (
          fn ===
          togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut
        )
          return togglePromise
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      expect(component.isPublishedGn()).toBe(false)

      const toggleCall = component.onTogglePublishGn(true)

      // Optimistic update should be applied immediately
      expect(component.isPublishedGn()).toBe(true)
      expect(component.isPublishing()).toBe(true)

      resolveToggle({ integrity_link_id: intlinkId, gn_is_published: true })
      await toggleCall

      expect(component.isPublishing()).toBe(false)
    })
  })
})
