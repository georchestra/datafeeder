import { Component, OnInit, computed, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
  getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
  listGroupsDataGroupsGet,
  listGroupsMetadataGroupsGet,
  listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
  upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut
} from '../../core/api/functions'
import {
  GroupItem,
  IntegrityLinkResponse,
  IntegrityLinkRule,
  RuleType
} from '../../core/api/models'
import {
  AuthorizationRulesComponent,
  RuleChangeEvent
} from '../../shared/components/authorization-rules/authorization-rules.component'

@Component({
  selector: 'app-authorizations',
  imports: [TranslatePipe, AuthorizationRulesComponent],
  templateUrl: './authorizations.component.html',
  host: { class: 'flex-1 min-h-0 flex flex-col' }
})
export class AuthorizationsComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)
  private readonly metadataRuleType: RuleType = 'METADATA'
  private readonly dataRuleType: RuleType = 'DATA'

  intlinkId = this.route.parent?.snapshot.paramMap.get('intlink_id') ?? null
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  rules = signal<IntegrityLinkRule[]>([])
  geonetworkGroups = signal<GroupItem[]>([])
  geoserverGroups = signal<GroupItem[]>([])
  metadataRules = computed(() =>
    this.rules().filter((r) => r.rule_type === this.metadataRuleType)
  )
  dataRules = computed(() =>
    this.rules().filter((r) => r.rule_type === this.dataRuleType)
  )

  ngOnInit(): void {
    if (this.intlinkId) {
      this.loadIntegrityLink(this.intlinkId)
      this.loadRules(this.intlinkId)
      this.loadGeonetworkGroups()
      this.loadGeoserverGroups()
    }
  }

  async onMetadataRuleChange(event: RuleChangeEvent): Promise<void> {
    await this.handleRuleChange(event, this.metadataRuleType)
  }

  async onDataRuleChange(event: RuleChangeEvent): Promise<void> {
    await this.handleRuleChange(event, this.dataRuleType)
  }

  private async handleRuleChange(
    event: RuleChangeEvent,
    ruleType: RuleType
  ): Promise<void> {
    if (!this.intlinkId) return
    const existingRule = this.rules().find(
      (r) => r.group_or_role === event.group.id && r.rule_type === ruleType
    )

    if (event.value === 'NONE') {
      if (existingRule?.id != null) {
        await this.api.invoke(
          deleteIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesRuleIdDelete,
          {
            integrity_link_id: this.intlinkId,
            rule_id: existingRule.id
          }
        )
      }
    } else {
      await this.api.invoke(
        upsertIntegrityLinkRuleIngestionIntegrityLinkIntegrityLinkIdRulesPut,
        {
          integrity_link_id: this.intlinkId,
          body: {
            group_or_role: event.group.id,
            rule_type: ruleType,
            rule_value: event.value as 'READ' | 'WRITE'
          }
        }
      )
    }
    await this.loadRules(this.intlinkId)
  }

  private async loadIntegrityLink(id: string): Promise<void> {
    const metadata = await this.api.invoke(
      getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
      { integrity_link_id: id }
    )
    this.integrityLink.set(metadata)
  }

  private async loadRules(id: string): Promise<void> {
    const rules = await this.api.invoke(
      listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
      { integrity_link_id: id }
    )
    this.rules.set(rules)
  }

  private async loadGeonetworkGroups(): Promise<void> {
    const groups = await this.api.invoke(listGroupsMetadataGroupsGet)
    this.geonetworkGroups.set(groups)
  }

  private async loadGeoserverGroups(): Promise<void> {
    const groups = await this.api.invoke(listGroupsDataGroupsGet)
    this.geoserverGroups.set(groups)
  }
}
