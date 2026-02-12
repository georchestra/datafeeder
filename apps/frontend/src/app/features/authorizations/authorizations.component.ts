import { Component, OnInit, computed, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import {
  getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
  listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet
} from '../../core/api/functions'
import {
  IntegrityLinkResponse,
  IntegrityLinkRule,
  RuleType
} from '../../core/api/models'
import { GeonetworkAuthorizationsComponent } from './geonetwork-authorizations.component'

@Component({
  selector: 'app-authorizations',
  imports: [TranslatePipe, GeonetworkAuthorizationsComponent],
  templateUrl: './authorizations.component.html'
})
export class AuthorizationsComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)
  private readonly metadataRuleType: RuleType = 'METADATA'

  intlinkId = this.route.parent?.snapshot.paramMap.get('intlink_id') ?? null
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  rules = signal<IntegrityLinkRule[]>([])
  metadataRules = computed(() =>
    this.rules().filter((r) => r.rule_type === this.metadataRuleType)
  )

  ngOnInit(): void {
    if (this.intlinkId) {
      this.loadIntegrityLink(this.intlinkId)
      this.loadRules(this.intlinkId)
    }
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
}
