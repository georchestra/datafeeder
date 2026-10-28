import { Component, effect, inject, input, output } from '@angular/core'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { TranslatePipe } from '@ngx-translate/core'
import { TextInputComponent } from 'geonetwork-ui'

marker('import.dataSource.database.schema')
marker('import.dataSource.database.table')

export interface DbData {
  schema: string
  table: string
}

@Component({
  selector: 'app-data-source-db',
  imports: [ReactiveFormsModule, TranslatePipe, TextInputComponent],
  templateUrl: './data-source-db.component.html'
})
export class DataSourceDbComponent {
  private fb = inject(FormBuilder)

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
