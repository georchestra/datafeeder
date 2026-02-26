import { TestBed } from '@angular/core/testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
  listGroupsDataGroupsGet,
  listGroupsMetadataGroupsGet,
  listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
  upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
} from '../../core/api/functions'
import { GroupItem, IntegrityLinkRule } from '../../core/api/models'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'
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
            'authorizations.ruleValue.read': 'Read',
            'authorizations.ruleValue.write': 'Write'
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
  //   403 on GET rules → unhandled promise rejection, rules stays empty   ❌
  //   403 on PUT/DELETE rule → unhandled promise rejection               ❌

  describe('Error handling', () => {
    it('should leave rules empty when listRules API returns 403 — unhandled rejection (❌)', async () => {
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

      const fixture = TestBed.createComponent(AuthorizationsComponent)
      const component = fixture.componentInstance

      // Call loadRules directly (bypassing ngOnInit) and catch the rejection to
      // avoid an unhandled promise rejection in the test runner.
      // This verifies that when loadRules throws, rules() stays empty (no try/catch
      // in the component means the signal is never updated on error).
      await (component as any).loadRules(intlinkId).catch(() => {})

      expect(component.rules()).toEqual([])
    })

    it('should leave rules unchanged when upsert returns 403 — unhandled rejection (❌)', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
        )
          return Promise.resolve(mockRules)
        if (fn === listGroupsMetadataGroupsGet)
          return Promise.resolve(mockGeonetworkGroups)
        if (fn === listGroupsDataGroupsGet)
          return Promise.resolve(mockGeoserverGroups)
        if (
          fn ===
          upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
        )
          return Promise.reject({ status: 403, message: 'Forbidden' })
        return Promise.resolve(null)
      })

      const fixture = TestBed.createComponent(AuthorizationsComponent)
      const component = fixture.componentInstance
      fixture.detectChanges()

      await vi.waitFor(() => expect(component.rules().length).toBe(2))

      // onMetadataRuleChange has no try/catch — the rejection propagates
      await component
        .onMetadataRuleChange({
          group: { id: 'org-1', label: 'Organization A' },
          value: 'WRITE'
        })
        .catch(() => {})

      // rules signal reflects last successful load, not the failed upsert
      expect(component.rules().length).toBe(2)
    })
  })
})
