import { TestBed } from '@angular/core/testing'
import { HttpErrorResponse } from '@angular/common/http'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
  listGroupsDataGroupsGet,
  listGroupsMetadataGroupsGet,
  listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
  togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut,
  togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut,
  upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
} from '../../core/api/functions'
import { GroupItem, IntegrityLinkRule } from '../../core/api/models'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
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
  let toastStore: OperationToastStore

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
            'authorizations.geonetwork.publishErrorMetadata.title':
              'Publication Error',
            'authorizations.geonetwork.publishErrorMetadata.defaultMessage':
              'An error occurred during publication',
            'i18nerror.publish.geonetwork':
              'Error publishing metadata to GeoNetwork',
            'authorizations.geoserver.publishErrorMetadata.title':
              'Publication Error',
            'authorizations.geoserver.publishErrorMetadata.defaultMessage':
              'An error occurred during GeoServer publication',
            'i18nerror.publish.geoserver': 'Error publishing layer to GeoServer'
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
    toastStore = TestBed.inject(OperationToastStore)
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
  //   403 on PUT/DELETE rule → toast added to OperationToastStore          ✅

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

    it('should add toast and leave rules unchanged when upsert returns 403 (✅)', async () => {
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

      expect(toastStore.toasts().length).toBe(1)
      expect(toastStore.toasts()[0].translationKey).toBe(
        'errors.operation.gnRightsEdit'
      )
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
      expect(component.isPublishedMetadata()).toBe(true)
      expect(component.isPublishingMetadata()).toBe(false)
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

      expect(component.isPublishedMetadata()).toBe(false)
    })

    it('should add gnPublish toast on generic error', async () => {
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

      expect(toastStore.toasts().length).toBe(1)
      expect(toastStore.toasts()[0].translationKey).toBe(
        'errors.operation.gnPublish'
      )
      expect(component.isPublishingMetadata()).toBe(false)
    })

    it('should add gnPublish toast with backend detail as translation key', async () => {
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
          return Promise.reject(
            new HttpErrorResponse({
              error: { detail: 'i18nerror.publish.geonetwork' },
              status: 400
            })
          )
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGn(true)

      expect(toastStore.toasts().length).toBe(1)
      expect(toastStore.toasts()[0].translationKey).toBe(
        'i18nerror.publish.geonetwork'
      )
      expect(component.isPublishingMetadata()).toBe(false)
    })

    it('should optimistically update isPublishedMetadata before API resolves', async () => {
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
      expect(component.isPublishedMetadata()).toBe(false)

      const toggleCall = component.onTogglePublishGn(true)

      // Optimistic update should be applied immediately
      expect(component.isPublishedMetadata()).toBe(true)
      expect(component.isPublishingMetadata()).toBe(true)

      resolveToggle({ integrity_link_id: intlinkId, gn_is_published: true })
      await toggleCall

      expect(component.isPublishingMetadata()).toBe(false)
    })

    it('should only update gn_is_published in the store, preserving other fields', async () => {
      store.integrityLink.set({
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: false,
        gs_is_published: false
      } as any)

      const updatedLink = {
        integrity_link_id: intlinkId,
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

      expect(store.integrityLink()?.gn_is_published).toBe(true)
      expect(store.integrityLink()?.gs_is_published).toBe(false) // other publish field untouched
      expect((store.integrityLink() as any)?.integrity_title).toBe('Test Link') // other fields preserved
    })
  })

  describe('onTogglePublishGs', () => {
    it('should call toggle publish API with publish=true and update signals on success', async () => {
      const updatedLink = {
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gs_is_published: true
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGs(true)

      expect(apiInvokeSpy).toHaveBeenCalledWith(
        togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut,
        { integrity_link_id: intlinkId, publish: true }
      )
      expect(component.isPublishedData()).toBe(true)
      expect(component.isPublishingData()).toBe(false)
    })

    it('should call toggle publish API with publish=false and update signals on success', async () => {
      store.integrityLink.set({
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gs_is_published: true
      } as any)

      const updatedLink = {
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gs_is_published: false
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGs(false)

      expect(component.isPublishedData()).toBe(false)
    })

    it('should add gsPublish toast on generic error', async () => {
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.reject(new Error('Network error'))
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGs(true)

      expect(toastStore.toasts().length).toBe(1)
      expect(toastStore.toasts()[0].translationKey).toBe(
        'errors.operation.gsPublish'
      )
      expect(component.isPublishingData()).toBe(false)
    })

    it('should add gsPublish toast with backend detail as translation key', async () => {
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.reject(
            new HttpErrorResponse({
              error: { detail: 'i18nerror.publish.geoserver' },
              status: 400
            })
          )
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGs(true)

      expect(toastStore.toasts().length).toBe(1)
      expect(toastStore.toasts()[0].translationKey).toBe(
        'i18nerror.publish.geoserver'
      )
      expect(component.isPublishingData()).toBe(false)
    })

    it('should optimistically update isPublishedData before API resolves', async () => {
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return togglePromise
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      expect(component.isPublishedData()).toBe(false)

      const toggleCall = component.onTogglePublishGs(true)

      expect(component.isPublishedData()).toBe(true)
      expect(component.isPublishingData()).toBe(true)

      resolveToggle({ integrity_link_id: intlinkId, gs_is_published: true })
      await toggleCall

      expect(component.isPublishingData()).toBe(false)
    })

    it('should revert isPublishedData to previous value on error', async () => {
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.reject(new Error('Server error'))
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      expect(component.isPublishedData()).toBe(false)

      await component.onTogglePublishGs(true)

      // Should revert back to false after error
      await vi.waitFor(() => expect(component.isPublishedData()).toBe(false))
      expect(toastStore.toasts().length).toBe(1)
    })

    it('should update rules signal from response.rules on success', async () => {
      const updatedRules: IntegrityLinkRule[] = [
        {
          id: 99,
          integrity_link_id: intlinkId,
          group_or_role: '*',
          rule_type: 'DATA',
          rule_value: 'READ'
        }
      ]
      const updatedLink = {
        integrity_link_id: intlinkId,
        gs_is_published: true,
        rules: updatedRules
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      await vi.waitFor(() => expect(component.rules().length).toBe(2))

      await component.onTogglePublishGs(true)

      expect(component.rules()).toEqual(updatedRules)
    })

    it('should not update rules signal when response.rules is undefined', async () => {
      const updatedLink = {
        integrity_link_id: intlinkId,
        gs_is_published: true
        // rules intentionally absent
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()
      await vi.waitFor(() => expect(component.rules().length).toBe(2))

      await component.onTogglePublishGs(true)

      expect(component.rules()).toEqual(mockRules)
    })

    it('should only update gs_is_published in the store, preserving other fields', async () => {
      store.integrityLink.set({
        integrity_link_id: intlinkId,
        integrity_title: 'Test Link',
        gn_is_published: false,
        gs_is_published: false
      } as any)

      const updatedLink = {
        integrity_link_id: intlinkId,
        gs_is_published: true
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
          togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut
        )
          return Promise.resolve(updatedLink)
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onTogglePublishGs(true)

      expect(store.integrityLink()?.gs_is_published).toBe(true)
      expect(store.integrityLink()?.gn_is_published).toBe(false) // other publish field untouched
      expect((store.integrityLink() as any)?.integrity_title).toBe('Test Link') // other fields preserved
    })
  })
})
