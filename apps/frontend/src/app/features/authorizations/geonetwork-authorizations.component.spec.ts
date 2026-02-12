import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { ApiConfiguration } from '../../core/api/api-configuration'
import { GroupItem, IntegrityLinkRule } from '../../core/api/models'
import { GeonetworkAuthorizationsComponent } from './geonetwork-authorizations.component'

describe('GeonetworkAuthorizationsComponent', () => {
  let httpMock: HttpTestingController

  const mockGroups: GroupItem[] = [
    { id: 'group-1', label: 'Administrators' },
    { id: 'group-2', label: 'Editors' },
    { id: 'group-3', label: 'Reviewers' }
  ]

  const mockRules: IntegrityLinkRule[] = [
    {
      id: 10,
      integrity_link_id: 'link-42',
      group_or_role: 'group-1',
      rule_type: 'METADATA',
      rule_value: 'READ'
    },
    {
      id: 11,
      integrity_link_id: 'link-42',
      group_or_role: 'group-2',
      rule_type: 'METADATA',
      rule_value: 'WRITE'
    }
  ]

  const tick = () => new Promise((resolve) => setTimeout(resolve, 10))

  const createComponent = () => {
    const fixture = TestBed.createComponent(GeonetworkAuthorizationsComponent)
    fixture.componentRef.setInput('intlinkId', 'link-42')
    fixture.componentRef.setInput('ruleType', 'METADATA')
    fixture.componentRef.setInput('rules', mockRules)
    fixture.detectChanges()
    return { fixture, component: fixture.componentInstance }
  }

  const flushInitialGroups = (groups: GroupItem[] = mockGroups) => {
    const req = httpMock.expectOne('http://localhost:8000/metadata/groups/')
    expect(req.request.method).toBe('GET')
    req.flush(groups)
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        GeonetworkAuthorizationsComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'authorizations.geonetwork.search': 'Search',
            'authorizations.ruleValue.none': 'None',
            'authorizations.ruleValue.read': 'Read',
            'authorizations.ruleValue.write': 'Write'
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
    const pending = httpMock.match(() => true)
    pending.forEach((req) => {
      if (!req.cancelled) req.flush([])
    })
    httpMock.verify()
  })

  describe('Creation & initial load', () => {
    it('should create the component', () => {
      const { component } = createComponent()
      flushInitialGroups()
      expect(component).toBeTruthy()
    })

    it('should call GET /metadata/groups/ on init and populate groups signal', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      expect(component.groups().length).toBe(3)
      expect(component.groups()[0].label).toBe('Administrators')
    })
  })

  describe('getRuleValue', () => {
    it('should return NONE when no matching rule exists', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      expect(
        component.getRuleValue({ id: 'group-3', label: 'Reviewers' })
      ).toBe('NONE')
    })

    it('should return the rule value when a matching rule exists', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      expect(
        component.getRuleValue({ id: 'group-1', label: 'Administrators' })
      ).toBe('READ')
      expect(component.getRuleValue({ id: 'group-2', label: 'Editors' })).toBe(
        'WRITE'
      )
    })
  })

  describe('Search filtering', () => {
    it('should return all groups when search is empty', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      expect(component.filteredGroups().length).toBe(3)
    })

    it('should filter groups case-insensitively by label', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      component.onSearchInput('admin')
      expect(component.filteredGroups().length).toBe(1)
      expect(component.filteredGroups()[0].label).toBe('Administrators')
    })

    it('should reset to all groups when clearSearch is called', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      component.onSearchInput('editor')
      expect(component.filteredGroups().length).toBe(1)

      component.clearSearch()
      expect(component.searchQuery()).toBe('')
      expect(component.filteredGroups().length).toBe(3)
    })
  })

  describe('onRuleChange — upsert', () => {
    it('should call PUT with correct body when setting a non-NONE value', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      const emitSpy = vi.spyOn(component.rulesChanged, 'emit')
      const promise = component.onRuleChange(
        { id: 'group-3', label: 'Reviewers' },
        'READ'
      )

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/link-42/rules'
      )
      expect(req.request.method).toBe('PUT')
      expect(req.request.body).toEqual({
        group_or_role: 'group-3',
        rule_type: 'METADATA',
        rule_value: 'READ'
      })
      req.flush({
        id: 20,
        integrity_link_id: 'link-42',
        group_or_role: 'group-3',
        rule_type: 'METADATA',
        rule_value: 'READ'
      })

      await promise
      expect(emitSpy).toHaveBeenCalled()
    })
  })

  describe('onRuleChange — delete', () => {
    it('should call DELETE when setting NONE on a group with an existing rule', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      const emitSpy = vi.spyOn(component.rulesChanged, 'emit')
      const promise = component.onRuleChange(
        { id: 'group-1', label: 'Administrators' },
        'NONE'
      )

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/link-42/rules/10'
      )
      expect(req.request.method).toBe('DELETE')
      req.flush(null)

      await promise
      expect(emitSpy).toHaveBeenCalled()
    })

    it('should emit rulesChanged without API call when setting NONE on a group with no rule', async () => {
      const { component } = createComponent()
      flushInitialGroups()
      await tick()

      const emitSpy = vi.spyOn(component.rulesChanged, 'emit')
      await component.onRuleChange(
        { id: 'group-3', label: 'Reviewers' },
        'NONE'
      )

      httpMock.expectNone(
        'http://localhost:8000/ingestion/integrity-link/link-42/rules'
      )
      expect(emitSpy).toHaveBeenCalled()
    })
  })

  describe('ruleChoices', () => {
    it('should contain exactly 3 choices: NONE, READ, WRITE', () => {
      const { component } = createComponent()
      flushInitialGroups()

      expect(component.ruleChoices.length).toBe(3)
      expect(component.ruleChoices.map((c) => c.value)).toEqual([
        'NONE',
        'READ',
        'WRITE'
      ])
    })
  })
})
