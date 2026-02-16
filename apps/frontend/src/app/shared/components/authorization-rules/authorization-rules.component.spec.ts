import { TestBed } from '@angular/core/testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { GroupItem, IntegrityLinkRule } from '../../../core/api/models'
import { AuthorizationRulesComponent } from './authorization-rules.component'

describe('AuthorizationRulesComponent', () => {
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

  const createComponent = () => {
    const fixture = TestBed.createComponent(AuthorizationRulesComponent)
    fixture.componentRef.setInput('groups', mockGroups)
    fixture.componentRef.setInput('rules', mockRules)
    fixture.componentRef.setInput('searchPlaceholder', 'Search groups')
    fixture.detectChanges()
    return { fixture, component: fixture.componentInstance }
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AuthorizationRulesComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'authorizations.ruleValue.none': 'None',
            'authorizations.ruleValue.read': 'Read',
            'authorizations.ruleValue.write': 'Write'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create the component', () => {
    const { component } = createComponent()
    expect(component).toBeTruthy()
  })

  describe('getRuleValue', () => {
    it('should return NONE when no matching rule exists', () => {
      const { component } = createComponent()
      expect(
        component.getRuleValue({ id: 'group-3', label: 'Reviewers' })
      ).toBe('NONE')
    })

    it('should return the rule value when a matching rule exists', () => {
      const { component } = createComponent()
      expect(
        component.getRuleValue({ id: 'group-1', label: 'Administrators' })
      ).toBe('READ')
      expect(component.getRuleValue({ id: 'group-2', label: 'Editors' })).toBe(
        'WRITE'
      )
    })
  })

  describe('Search filtering', () => {
    it('should return all groups when search is empty', () => {
      const { component } = createComponent()
      expect(component.filteredGroups().length).toBe(3)
    })

    it('should filter groups case-insensitively by label', () => {
      const { component } = createComponent()
      component.searchQuery.set('admin')
      expect(component.filteredGroups().length).toBe(1)
      expect(component.filteredGroups()[0].label).toBe('Administrators')
    })

    it('should reset to all groups when clearSearch is called', () => {
      const { component } = createComponent()
      component.searchQuery.set('editor')
      expect(component.filteredGroups().length).toBe(1)

      component.searchQuery.set('')
      expect(component.searchQuery()).toBe('')
      expect(component.filteredGroups().length).toBe(3)
    })
  })

  describe('ruleChange output', () => {
    it('should emit ruleChange with correct payload', () => {
      const { component } = createComponent()
      const emitSpy = vi.spyOn(component.ruleChange, 'emit')

      const group = { id: 'group-3', label: 'Reviewers' }
      component.onDropdownChange(group, 'READ')

      expect(emitSpy).toHaveBeenCalledWith({ group, value: 'READ' })
    })
  })

  describe('ruleChoices', () => {
    it('should contain exactly 3 choices: NONE, READ, WRITE', () => {
      const { component } = createComponent()
      expect(component.ruleChoices.length).toBe(3)
      expect(component.ruleChoices.map((c) => c.value)).toEqual([
        'NONE',
        'READ',
        'WRITE'
      ])
    })
  })
})
