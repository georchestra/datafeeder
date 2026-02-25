import {
  Component,
  computed,
  inject,
  input,
  output,
  signal
} from '@angular/core'
import { TranslateService } from '@ngx-translate/core'
import { DropdownSelectorComponent, DropdownChoice } from 'geonetwork-ui'
import { GroupItem, IntegrityLinkRule } from '../../../core/api/models'
import { SearchInputComponent } from '../search-input/search-input.component'

export interface RuleChangeEvent {
  group: GroupItem
  value: string
}

@Component({
  selector: 'app-authorization-rules',
  imports: [DropdownSelectorComponent, SearchInputComponent],
  templateUrl: './authorization-rules.component.html'
})
export class AuthorizationRulesComponent {
  private translate = inject(TranslateService)

  groups = input<GroupItem[]>([])
  rules = input<IntegrityLinkRule[]>([])
  searchPlaceholder = input('')
  ruleChange = output<RuleChangeEvent>()

  searchQuery = signal('')
  filteredGroups = computed(() => {
    const query = this.searchQuery().toLowerCase()
    if (!query) return this.groups()
    return this.groups()
      .filter((g) => g.label.toLowerCase().includes(query))
      .sort((a, b) => a.label.localeCompare(b.label))
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

  getRuleValue(group: GroupItem): string {
    const rule = this.rules().find((r) => r.group_or_role === group.id)
    return rule?.rule_value ?? 'NONE'
  }

  onDropdownChange(group: GroupItem, value: string): void {
    this.ruleChange.emit({ group, value })
  }
}
