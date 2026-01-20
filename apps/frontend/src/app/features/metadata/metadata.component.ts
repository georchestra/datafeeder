import { CommonModule } from '@angular/common'
import { Component, OnInit, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import {
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { map, take, tap } from 'rxjs'
import { Api } from '../../core/api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../../core/api/functions'
import { IntegrityLinkResponse } from '../../core/api/models'

// Taken from libs/feature/editor/src/lib/fields.config.ts in GN-UI
marker('editor.record.form.field.uniqueIdentifier')
marker('editor.record.form.field.constraintsShortcuts')
marker('editor.record.form.field.legalConstraints')
marker('editor.record.form.field.securityConstraints')
marker('editor.record.form.field.otherConstraints')
marker('editor.record.form.field.license')
marker('editor.record.form.field.resourceCreated')
marker('editor.record.form.field.resourceIdentifier')
marker('editor.record.form.field.resourceUpdated')
marker('editor.record.form.field.recordUpdated')
marker('editor.record.form.field.updateFrequency')
marker('editor.record.form.field.temporalExtents')
marker('editor.record.form.field.title')
marker('editor.record.form.field.abstract')
marker('editor.record.form.field.overviews')
marker('editor.record.form.field.spatialExtents')
marker('editor.record.form.field.onlineResources')
marker('editor.record.form.field.onlineLinkResources')
marker('editor.record.form.section.about.label')
marker('editor.record.form.section.about.description')
marker('editor.record.form.section.geographicalCoverage.label')
marker('editor.record.form.section.associatedResources.label')
marker('editor.record.form.section.associatedResources.description')
marker('editor.record.form.section.annexes.label')
marker('editor.record.form.section.annexes.description')
marker('editor.record.form.section.classification.label')
marker('editor.record.form.section.classification.description')
marker('editor.record.form.section.topics.label')
marker('editor.record.form.section.topics.description')
marker('editor.record.form.section.useAndAccessConditions.label')
marker('editor.record.form.section.dataManagers.label')
marker('editor.record.form.section.dataManagers.description')
marker('editor.record.form.section.metadataPointOfContact.label')
marker('editor.record.form.section.metadataPointOfContact.description')
marker('editor.record.form.page.description')
marker('editor.record.form.page.resources')
marker('editor.record.form.page.accessAndContact')

marker('editor.record.form.license.cc-by')
marker('editor.record.form.license.cc-by-sa')
marker('editor.record.form.license.cc-zero')
marker('editor.record.form.license.etalab')
marker('editor.record.form.license.etalab-v2')
marker('editor.record.form.license.odbl')
marker('editor.record.form.license.odc-by')
marker('editor.record.form.license.pddl')
marker('editor.record.form.license.unknown')

marker('editor.record.form.topics.inspire.biota')
marker('editor.record.form.topics.inspire.boundaries')
marker('editor.record.form.topics.inspire.climatology')
marker('editor.record.form.topics.inspire.economy')
marker('editor.record.form.topics.inspire.elevation')
marker('editor.record.form.topics.inspire.environnement')
marker('editor.record.form.topics.inspire.farming')
marker('editor.record.form.topics.inspire.geoscientific')
marker('editor.record.form.topics.inspire.health')
marker('editor.record.form.topics.inspire.imagery')
marker('editor.record.form.topics.inspire.intelligence')
marker('editor.record.form.topics.inspire.location')
marker('editor.record.form.topics.inspire.oceans')
marker('editor.record.form.topics.inspire.planning')
marker('editor.record.form.topics.inspire.society')
marker('editor.record.form.topics.inspire.structure')
marker('editor.record.form.topics.inspire.transportation')
marker('editor.record.form.topics.inspire.utilities')
marker('editor.record.form.topics.inspire.waters')

// Temporal extent
marker('editor.record.form.updateFrequency.planned')
marker('editor.record.form.temporalExtents.addDate')
marker('editor.record.form.temporalExtents.addRange')
marker('editor.record.form.temporalExtents.date')
marker('editor.record.form.temporalExtents.range')

// Taken from libs/common/domain/src/lib/model/record/metadata.model.ts in GN-UI
marker('domain.record.updateFrequency.unknown')
marker('domain.record.updateFrequency.notPlanned')
marker('domain.record.updateFrequency.asNeeded')
marker('domain.record.updateFrequency.irregular')
marker('domain.record.updateFrequency.continual')
marker('domain.record.updateFrequency.periodic')

marker('domain.record.updateFrequency.day')
marker('domain.record.updateFrequency.week')
marker('domain.record.updateFrequency.month')
marker('domain.record.updateFrequency.year')

marker('domain.record.updateFrequency.daily')
marker('domain.record.updateFrequency.weekly')
marker('domain.record.updateFrequency.fortnightly')
marker('domain.record.updateFrequency.monthly')
marker('domain.record.updateFrequency.quarterly')
marker('domain.record.updateFrequency.biannually')
marker('domain.record.updateFrequency.annually')
marker('domain.record.updateFrequency.semimonthly')
marker('domain.record.updateFrequency.biennially')

// keywords and topics
marker('editor.record.form.keywords.placeholder')
marker('editor.record.form.topics.placeholder')
marker('editor.record.form.keywords.place.placeholder')
marker('editor.record.placeKeywordWithoutLabel')

// Taken from libs/ui/elements/src/lib/image-input in GN-UI
marker('input.image.altTextPlaceholder')
marker('input.image.delete')
marker('input.image.displayAltTextInput')
marker('input.image.displayUrlInput')

// Taken from libs/ui/inputs/src/lib/file-input in GN-UI
marker('input.file.selectFileLabel')
marker('input.file.dropFileLabel')
marker('input.file.orInputUrl')

// Online Resource
marker('editor.record.form.field.onlineResource.modify')

// Constraints
marker('editor.record.form.constraint.add.legalConstraints')
marker('editor.record.form.constraint.add.otherConstraints')
marker('editor.record.form.constraint.add.securityConstraints')
marker('editor.record.form.constraint.header.legalConstraints')
marker('editor.record.form.constraint.header.otherConstraints')
marker('editor.record.form.constraint.header.securityConstraints')
marker('editor.record.form.constraint.legalConstraints')
marker('editor.record.form.constraint.markdown.placeholder')
marker('editor.record.form.constraint.not.applicable')
marker('editor.record.form.constraint.not.known')
marker('editor.record.form.constraint.otherConstraints')
marker('editor.record.form.constraint.securityConstraints')

// Contacts
marker('editor.record.form.field.contacts.noContact')
marker('editor.record.form.field.contacts.placeholder')
marker('editor.record.form.field.contactsForResource.noContact')
marker('editor.record.form.field.contactsForResource.placeholder')

marker('domain.contact.role.author')
marker('domain.contact.role.collaborator')
marker('domain.contact.role.contributor')
marker('domain.contact.role.custodian')
marker('domain.contact.role.distributor')
marker('domain.contact.role.editor')
marker('domain.contact.role.funder')
marker('domain.contact.role.mediator')
marker('domain.contact.role.originator')
marker('domain.contact.role.other')
marker('domain.contact.role.owner')
marker('domain.contact.role.point_of_contact')
marker('domain.contact.role.principal_investigator')
marker('domain.contact.role.processor')
marker('domain.contact.role.publisher')
marker('domain.contact.role.resource_provider')
marker('domain.contact.role.rights_holder')
marker('domain.contact.role.sponsor')
marker('domain.contact.role.stakeholder')
marker('domain.contact.role.unspecified')
marker('domain.contact.role.user')

@Component({
  selector: 'app-metadata',
  imports: [CommonModule, RecordFormComponent],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css'
})
export class MetadataComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)

  intlink_id: string | null = null

  isRecordLoaded$ = this.editor.record$.pipe(map((record) => !!record))

  ngOnInit(): void {
    this.intlink_id = this.route.snapshot.paramMap.get('intlink_id')
    if (this.intlink_id) {
      this.loadMetadata(this.intlink_id)
    }
  }

  private async loadMetadata(intlink_id: string): Promise<void> {
    try {
      const response: IntegrityLinkResponse = await this.api.invoke(
        getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
        {
          integrity_link_id: intlink_id
        }
      )

      this.recordsRepository
        .openRecordForEdition(response.metadata_id)
        .pipe(
          take(1),
          tap(([currentRecord, currentRecordSource]) => {
            this.editor.openRecord(currentRecord, currentRecordSource)
            // TODO: remove when navigation between pages is implemented
            this.editor.setCurrentPage(0)
          })
        )
        .subscribe()
    } catch (error) {
      console.error('Error loading metadata:', error)
    }
  }
}
