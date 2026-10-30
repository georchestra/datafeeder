import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output
} from '@angular/core'
import { toObservable, toSignal } from '@angular/core/rxjs-interop'
import { NgTemplateOutlet } from '@angular/common'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { MatTooltipModule } from '@angular/material/tooltip'
import { merge } from 'rxjs'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirCheckCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  type DropdownChoice,
  DropdownSelectorComponent,
  TextInputComponent
} from 'geonetwork-ui'
import type {
  SourceDatabaseSummary,
  SourceSchema
} from '../../../core/api/models'

// Access type badges, translated from the database type
marker('import.dataSource.database.copy')
marker('import.dataSource.database.direct_access')

const NONE: DropdownChoice = { value: '', label: '-' }

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
    MatTooltipModule,
    TranslatePipe,
    NgIconComponent,
    DropdownSelectorComponent,
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
  sourceSchemas = input<SourceSchema[]>([])
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

  private schema = toSignal(this.form.controls.schema.valueChanges, {
    initialValue: ''
  })

  schemaChoices = computed<DropdownChoice[]>(() => [
    NONE,
    ...this.sourceSchemas().map((s) => ({
      value: s.schema_name,
      label: s.schema_name
    }))
  ])

  tableChoices = computed<DropdownChoice[]>(() => [
    NONE,
    ...(this.sourceSchemas()
      .find((s) => s.schema_name === this.schema())
      ?.tables.map((table) => ({ value: table, label: table })) ?? [])
  ])

  constructor() {
    effect(() => {
      const init = this.initialValue()
      if (init && !this.form.dirty) {
        this.form.patchValue(init)
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

  displayName(db: SourceDatabaseSummary): string {
    return db.label ? `${db.key} ${db.label}` : db.key
  }

  // Schema, table and title belong to the database: cleared when it changes
  select(key: string): void {
    this.form.reset()
    this.selectedKey.set(key)
  }

  selectSchema(schema: string): void {
    this.form.patchValue({ schema, table: '' })
  }

  private emit(): void {
    this.dbDataChanged.emit({
      key: this.selectedKey(),
      ...this.form.getRawValue()
    })
  }
}
