import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output
} from '@angular/core'
import { toObservable } from '@angular/core/rxjs-interop'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { merge } from 'rxjs'
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
marker('import.configuration.datasetTitle')

export interface DbData {
  key: string
  schema: string
  table: string
  // Direct access only: the title is asked in the first step
  title?: string
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

  sourceDatabases = input<SourceDatabaseSummary[]>([])
  initialValue = input<DbData | null>(null)
  dbDataChanged = output<DbData>()

  // ponytail: first database preselected until the database picker lands
  selectedKey = linkedSignal(
    () => this.initialValue()?.key || this.sourceDatabases()[0]?.key || ''
  )
  sourceDatabase = computed(
    () =>
      this.sourceDatabases().find((db) => db.key === this.selectedKey()) ?? null
  )

  form = this.fb.group({
    schema: this.fb.control<string>(''),
    table: this.fb.control<string>(''),
    title: this.fb.control<string>('')
  })

  constructor() {
    effect(() => {
      const init = this.initialValue()
      if (init && !this.form.dirty) {
        this.form.patchValue(init, { emitEvent: false })
      }
    })

    // The title belongs to the chosen table: cleared when it changes
    merge(
      this.form.controls.schema.valueChanges,
      this.form.controls.table.valueChanges
    ).subscribe(() =>
      this.form.controls.title.setValue('', { emitEvent: false })
    )

    // The key also changes outside the form: preselected on init, or once the
    // source databases are loaded
    merge(toObservable(this.selectedKey), this.form.valueChanges).subscribe(
      () => this.emit()
    )
  }

  private emit(): void {
    const value = this.form.getRawValue()
    this.dbDataChanged.emit({
      key: this.selectedKey(),
      schema: value.schema || '',
      table: value.table || '',
      title: value.title || ''
    })
  }
}
