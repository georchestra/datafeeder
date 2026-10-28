import { Component, effect, inject, input, output } from '@angular/core'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirCheckCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { TextInputComponent } from 'geonetwork-ui'
import type { SourceDatabaseSummary } from '../../../core/api/models'

marker('import.dataSource.database.schema')
marker('import.dataSource.database.table')
marker('import.dataSource.database.copy')
marker('import.dataSource.database.direct_access')

export interface DbData {
  schema: string
  table: string
}

@Component({
  selector: 'app-data-source-db',
  imports: [
    ReactiveFormsModule,
    TranslatePipe,
    NgIconComponent,
    TextInputComponent
  ],
  templateUrl: './data-source-db.component.html',
  providers: [provideIcons({ iconoirCheckCircle })]
})
export class DataSourceDbComponent {
  private fb = inject(FormBuilder)

  sourceDatabase = input<SourceDatabaseSummary | null>(null)
  initialValue = input<DbData | null>(null)
  dbDataChanged = output<DbData>()

  form = this.fb.group({
    schema: this.fb.control<string>(''),
    table: this.fb.control<string>('')
  })

  constructor() {
    effect(() => {
      const init = this.initialValue()
      if (init && !this.form.dirty) {
        this.form.setValue(init, { emitEvent: false })
      }
    })

    this.form.valueChanges.subscribe((value) => {
      this.dbDataChanged.emit({
        schema: value.schema || '',
        table: value.table || ''
      })
    })
  }
}
