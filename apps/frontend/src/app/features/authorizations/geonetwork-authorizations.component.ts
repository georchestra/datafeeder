import { Component, OnInit, inject, input, signal } from '@angular/core'
import { DropdownSelectorComponent, DropdownChoice } from 'geonetwork-ui'
import { Api } from '../../core/api/api'
import { listGroupsMetadataGroupsGet } from '../../core/api/functions'
import { GroupItem, IntegrityLinkRule } from '../../core/api/models'

@Component({
  selector: 'app-geonetwork-authorizations',
  imports: [DropdownSelectorComponent],
  templateUrl: './geonetwork-authorizations.component.html'
})
export class GeonetworkAuthorizationsComponent implements OnInit {
  private api = inject(Api)

  rules = input<IntegrityLinkRule[]>([])
  groups = signal<GroupItem[]>([])

  ruleChoices: DropdownChoice[] = [
    { value: 'NONE', label: 'None' },
    { value: 'READ', label: 'Read' },
    { value: 'WRITE', label: 'Write' }
  ]

  ngOnInit(): void {
    this.loadGroups()
  }

  getRuleValue(group: GroupItem): string {
    const rule = this.rules().find((r) => r.group_or_role === group.label)
    return rule?.rule_value ?? 'NONE'
  }

  // eslint-disable-next-line no-unused-vars
  onRuleChange(group: GroupItem, value: string): void {
    // Save logic deferred — backend CRUD endpoints don't exist yet
  }

  private async loadGroups(): Promise<void> {
    const groups = await this.api.invoke(listGroupsMetadataGroupsGet)
    this.groups.set(groups)
  }
}
