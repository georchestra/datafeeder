import { NgClass } from '@angular/common'
import {
  Component,
  OnInit,
  computed,
  effect,
  inject,
  signal
} from '@angular/core'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
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
import { GroupItem, IntegrityLinkRule, RuleType } from '../../core/api/models'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import {
  AuthorizationRulesComponent,
  RuleChangeEvent
} from '../../shared/components/authorization-rules/authorization-rules.component'
import { UiAlertBoxComponent } from '../../shared/components/ui-alert-box/ui-alert-box.component'
import { CheckToggleComponent, SpinningLoaderComponent } from 'geonetwork-ui'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('authorizations.geonetwork')
marker('authorizations.geonetwork.search')
marker('authorizations.geoserver')
marker('authorizations.geoserver.search')
marker('authorizations.title')
marker('authorizations.geonetwork.publicAccess')
marker('authorizations.geonetwork.publicAccess.value.public')
marker('authorizations.geonetwork.publicAccess.value.restricted')
marker('authorizations.geonetwork.publishErrorMetadata.title')
marker('authorizations.geonetwork.publishErrorMetadata.defaultMessage')
marker('authorizations.geoserver.publicAccess')
marker('authorizations.geoserver.publicAccess.value.public')
marker('authorizations.geoserver.publicAccess.value.restricted')
marker('authorizations.geoserver.publishErrorMetadata.title')
marker('authorizations.geoserver.publishErrorMetadata.defaultMessage')
marker('authorizations.geoserver.publishErrorData.title')
marker('i18nerror.publish.geonetwork')
marker('i18nerror.publish.geoserver')

@Component({
  selector: 'app-authorizations',
  imports: [
    NgClass,
    CheckToggleComponent,
    TranslatePipe,
    AuthorizationRulesComponent,
    SpinningLoaderComponent,
    UiAlertBoxComponent
  ],
  templateUrl: './authorizations.component.html',
  host: { class: 'flex-1 min-h-0 flex flex-col' }
})
export class AuthorizationsComponent implements OnInit {
  private api = inject(Api)
  readonly store = inject(IntegrityLinkStore)
  private translate = inject(TranslateService)
  private readonly metadataRuleType: RuleType = 'METADATA'
  private readonly dataRuleType: RuleType = 'DATA'

  intlinkId = this.store.intlinkId()
  rules = signal<IntegrityLinkRule[]>([])
  geonetworkGroups = signal<GroupItem[]>([])
  geoserverGroups = signal<GroupItem[]>([])
  loadError = signal<string | null>(null)
  mutationError = signal<string | null>(null)
  isPublishedMetadata = signal<boolean>(false)
  isPublishedData = signal<boolean>(false)
  isPublishingMetadata = signal<boolean>(false)
  isPublishingData = signal<boolean>(false)
  publishErrorMetadata = signal<string | null>(null)
  publishErrorData = signal<string | null>(null)

  metadataRules = computed(() =>
    this.rules().filter((r) => r.rule_type === this.metadataRuleType)
  )
  dataRules = computed(() =>
    this.rules().filter((r) => r.rule_type === this.dataRuleType)
  )

  constructor() {
    effect(() => {
      const integrityLink = this.store.integrityLink()
      if (integrityLink) {
        this.isPublishedMetadata.set(integrityLink.gn_is_published ?? false)
        this.isPublishedData.set(integrityLink.gs_is_published ?? false)
      }
    })
  }

  ngOnInit(): void {
    if (this.intlinkId) {
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

  async onTogglePublishGn(publish: boolean): Promise<void> {
    const previousValue = this.isPublishedMetadata()
    if (!this.intlinkId) return

    // Clear any previous error
    this.publishErrorMetadata.set(null)

    // Optimistically update the UI
    this.isPublishedMetadata.set(publish)
    this.isPublishingMetadata.set(true)

    try {
      const response = await this.api.invoke(
        togglePublishGnIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGnPut,
        {
          integrity_link_id: this.intlinkId,
          publish: publish
        }
      )
      // Update signal with the response value
      this.isPublishedMetadata.set(response.gn_is_published ?? false)
      this.store.integrityLink.set(response)
    } catch (error) {
      console.error('Failed to toggle publish status:', error)

      // Set error message
      let errorMessage = this.translate.instant(
        'authorizations.geonetwork.publishErrorMetadata.defaultMessage'
      )

      // Check if error has a detail property (i18n key from backend)
      if (error.error?.detail) {
        errorMessage = this.translate.instant(error.error.detail)
      } else if (error instanceof Error) {
        errorMessage = error.message
      }

      this.publishErrorMetadata.set(errorMessage)

      // Force re-render by setting to opposite first, then back to previous
      this.isPublishedMetadata.set(!previousValue)
      setTimeout(() => {
        this.isPublishedMetadata.set(
          this.store.integrityLink()?.gn_is_published ?? false
        )
      }, 0)
    } finally {
      this.isPublishingMetadata.set(false)
    }
  }

  async onTogglePublishGs(publish: boolean): Promise<void> {
    const previousValue = this.isPublishedData()
    if (!this.intlinkId) return

    this.publishErrorData.set(null)
    this.isPublishedData.set(publish)
    this.isPublishingData.set(true)

    try {
      const response = await this.api.invoke(
        togglePublishGsIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdPublishGsPut,
        {
          integrity_link_id: this.intlinkId,
          publish: publish
        }
      )
      this.isPublishedData.set(response.gs_is_published ?? false)
      this.store.integrityLink.set(response)
      if (response.rules !== undefined) {
        this.rules.set(response.rules)
      }
    } catch (error) {
      console.error('Failed to toggle GeoServer publish status:', error)

      let errorMessage = this.translate.instant(
        'authorizations.geoserver.publishErrorData.defaultMessage'
      )

      if (error.error?.detail) {
        errorMessage = this.translate.instant(error.error.detail)
      } else if (error instanceof Error) {
        errorMessage = error.message
      }

      this.publishErrorData.set(errorMessage)

      this.isPublishedData.set(!previousValue)
      setTimeout(() => {
        this.isPublishedData.set(
          this.store.integrityLink()?.gs_is_published ?? false
        )
      }, 0)
    } finally {
      this.isPublishingData.set(false)
    }
  }

  private async handleRuleChange(
    event: RuleChangeEvent,
    ruleType: RuleType
  ): Promise<void> {
    if (!this.intlinkId) return
    this.mutationError.set(null)
    const existingRule = this.rules().find(
      (r) => r.group_or_role === event.group.id && r.rule_type === ruleType
    )

    try {
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
    } catch (error) {
      console.error('Failed to update rule:', error)
      this.mutationError.set('authorizations.error.mutation')
    }
  }

  private async loadRules(id: string): Promise<void> {
    this.loadError.set(null)
    try {
      const rules = await this.api.invoke(
        listIntegrityLinkRulesIngestionIntegrityLinkIntegrityLinkIdRulesGet,
        { integrity_link_id: id }
      )
      this.rules.set(rules)
    } catch (error) {
      console.error('Failed to load rules:', error)
      this.loadError.set('authorizations.error.load')
    }
  }

  private async loadGeonetworkGroups(): Promise<void> {
    try {
      const groups = await this.api.invoke(listGroupsMetadataGroupsGet)
      this.geonetworkGroups.set(groups)
    } catch (error) {
      console.error('Failed to load GeoNetwork groups:', error)
    }
  }

  private async loadGeoserverGroups(): Promise<void> {
    try {
      const groups = await this.api.invoke(listGroupsDataGroupsGet)
      this.geoserverGroups.set(groups)
    } catch (error) {
      console.error('Failed to load GeoServer groups:', error)
    }
  }
}
