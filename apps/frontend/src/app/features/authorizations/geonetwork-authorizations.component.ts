import {
  Component,
  OnInit,
  computed,
  inject,
  input,
  output,
  signal
} from '@angular/core'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { DropdownSelectorComponent, DropdownChoice } from 'geonetwork-ui'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
  listGroupsMetadataGroupsGet,
  upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
} from '../../core/api/functions'
import { GroupItem, IntegrityLinkRule, RuleType } from '../../core/api/models'
import { SearchInputComponent } from '../../shared/components/search-input/search-input.component'

@Component({
  selector: 'app-geonetwork-authorizations',
  imports: [DropdownSelectorComponent, SearchInputComponent, TranslatePipe],
  templateUrl: './geonetwork-authorizations.component.html'
})
export class GeonetworkAuthorizationsComponent implements OnInit {
  private api = inject(Api)
  private translate = inject(TranslateService)

  intlinkId = input.required<string>()
  ruleType = input.required<RuleType>()
  rules = input<IntegrityLinkRule[]>([])
  rulesChanged = output<void>()
  groups = signal<GroupItem[]>([])
  searchQuery = signal('')
  filteredGroups = computed(() => {
    const query = this.searchQuery().toLowerCase()
    if (!query) return this.groups()
    return this.groups().filter((g) => g.label.toLowerCase().includes(query))
  })

  ruleChoices: DropdownChoice[] = [
    {
      value: 'NONE',
      label: this.translate.instant('authorizations.ruleValue.none')
    },
    {
      value: 'READ',
      label: this.translate.instant('authorizations.ruleValue.read')
    },
    {
      value: 'WRITE',
      label: this.translate.instant('authorizations.ruleValue.write')
    }
  ]

  ngOnInit(): void {
    this.loadGroups()
  }

  getRuleValue(group: GroupItem): string {
    const rule = this.rules().find((r) => r.group_or_role === group.id)
    return rule?.rule_value ?? 'NONE'
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value)
  }

  clearSearch(): void {
    this.searchQuery.set('')
  }

  async onRuleChange(group: GroupItem, value: string): Promise<void> {
    const existingRule = this.rules().find((r) => r.group_or_role === group.id)

    if (value === 'NONE') {
      if (existingRule?.id != null) {
        await this.api.invoke(
          deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
          {
            integrity_link_id: this.intlinkId(),
            rule_id: existingRule.id
          }
        )
      }
    } else {
      await this.api.invoke(
        upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut,
        {
          integrity_link_id: this.intlinkId(),
          body: {
            group_or_role: group.id,
            rule_type: this.ruleType(),
            rule_value: value as 'READ' | 'WRITE'
          }
        }
      )
    }
    this.rulesChanged.emit()
  }

  private async loadGroups(): Promise<void> {
    const groups = await this.api.invoke(listGroupsMetadataGroupsGet)
    this.groups.set(groups)
  }
}
