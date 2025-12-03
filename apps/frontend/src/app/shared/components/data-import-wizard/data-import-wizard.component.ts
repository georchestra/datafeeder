import { Component, signal, computed } from '@angular/core'
import { MatTabsModule } from '@angular/material/tabs'
import { MatIconModule } from '@angular/material/icon'
import { MatButtonModule } from '@angular/material/button'
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
    MatButtonModule,
    DataSourceSelectorComponent,
    DatasetConfigurationComponent
  ],
  templateUrl: './data-import-wizard.component.html',
  styleUrls: ['./data-import-wizard.component.scss']
})
export class DataImportWizardComponent {
  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>({
    source: { type: 'url', url: '' }
  })

  validSource = computed(() => {
    const url = this.importData().source.url
    return url.length > 0 && /^https?:\/\/.+/.test(url)
  })

  onSourceChanged(data: SourceData) {
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }
}
