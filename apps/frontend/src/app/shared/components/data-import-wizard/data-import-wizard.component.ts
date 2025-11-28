import { Component, signal } from '@angular/core'
import { MatTabsModule } from '@angular/material/tabs'
import { MatIconModule } from '@angular/material/icon'
import { DataSourceSelectorComponent } from '../data-source-selector/data-source-selector.component'
import { DatasetConfigurationComponent } from '../dataset-configuration/dataset-configuration.component'
import type { SourceData } from '../data-source-selector/data-source-selector.component'

export interface ImportWizardData {
  source: SourceData
}

@Component({
  selector: 'app-data-import-wizard',
  imports: [
    MatTabsModule,
    MatIconModule,
    DataSourceSelectorComponent,
    DatasetConfigurationComponent
  ],
  templateUrl: './data-import-wizard.component.html'
})
export class DataImportWizardComponent {
  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>({
    source: { type: 'url', url: '' }
  })

  onSourceChanged(data: SourceData) {
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }
}
