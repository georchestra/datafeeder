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
import { NgTemplateOutlet } from '@angular/common'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { merge } from 'rxjs'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirCheckCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { TextInputComponent } from 'geonetwork-ui'
import type { SourceDatabaseSummary } from '../../../core/api/models'

// Access type badges, translated from the database type
marker('import.dataSource.database.copy')
marker('import.dataSource.database.direct_access')

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
    NgTemplateOutlet,
    ReactiveFormsModule,
    TranslatePipe,
    NgIconComponent,
    TextInputComponent
  ],
  templateUrl: './data-source-db.component.html',
  providers: [
    provideIcons({ iconoirCheckCircle }),
    provideNgIconsConfig({ size: '1rem' })
  ]
})
export class DataSourceDbComponent {
  private fb = inject(FormBuilder)

  sourceDatabases = input<SourceDatabaseSummary[]>([])
  initialValue = input<DbData | null>(null)
  dbDataChanged = output<DbData>()

  selectedKey = linkedSignal(() => this.initialValue()?.key ?? '')
  sourceDatabase = computed(
    () =>
      this.sourceDatabases().find((db) => db.key === this.selectedKey()) ?? null
  )

  form = this.fb.nonNullable.group({
    schema: '',
    table: '',
    title: ''
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

    // The key changes outside the form: from initialValue or select()
    merge(toObservable(this.selectedKey), this.form.valueChanges).subscribe(
      () => this.emit()
    )
  }

  // Schema, table and title belong to the database: cleared when it changes
  select(key: string): void {
    this.form.reset(undefined, { emitEvent: false })
    this.selectedKey.set(key)
  }

  private emit(): void {
    this.dbDataChanged.emit({
      key: this.selectedKey(),
      ...this.form.getRawValue()
    })
  }
}
