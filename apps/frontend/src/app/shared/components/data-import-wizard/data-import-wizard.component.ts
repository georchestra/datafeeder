import { Component, signal, effect, inject } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { debounceTime, switchMap, catchError, of, tap } from 'rxjs'
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
  private http = inject(HttpClient)

  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>({
    source: { type: 'url', url: '' }
  })

  validSource = signal(false)
  validating = signal(false)

  constructor() {
    effect((onCleanup) => {
      const url = this.importData().source.url

      // Basic format validation
      if (!url || !/^https?:\/\/.+/.test(url)) {
        this.validSource.set(false)
        this.validating.set(false)
        return
      }

      // Start validation
      this.validating.set(true)

      const subscription = of(url) // TODO proxify request to avoid CORS issues
        .pipe(
          debounceTime(300),
          tap(() => this.validating.set(true)),
          switchMap((url) =>
            this.http
              .head(url, { observe: 'response' })
              .pipe(catchError(() => of(null)))
          ),
          tap(() => this.validating.set(false))
        )
        .subscribe((response) => {
          this.validSource.set(response?.status === 200)
        })

      onCleanup(() => {
        subscription.unsubscribe()
        this.validating.set(false)
      })
    })
  }

  onSourceChanged(data: SourceData) {
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }
}
