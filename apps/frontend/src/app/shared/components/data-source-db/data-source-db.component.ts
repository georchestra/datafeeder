import {
  Component,
  computed,
  effect,
  input,
  linkedSignal,
  output
} from '@angular/core'
import { NgTemplateOutlet } from '@angular/common'
import { MatTooltipModule } from '@angular/material/tooltip'
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

const EMPTY: DbData = { key: '', schema: '', table: '', title: '' }

@Component({
  selector: 'app-data-source-db',
  imports: [
    NgTemplateOutlet,
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
  sourceDatabases = input<SourceDatabaseSummary[]>([])
  sourceSchemas = input<SourceSchema[]>([])
  initialValue = input<DbData | null>(null)
  dbDataChanged = output<DbData>()

  formData = linkedSignal<DbData>(() => ({
    ...EMPTY,
    ...this.initialValue()
  }))

  sourceDatabase = computed(
    () =>
      this.sourceDatabases().find((db) => db.key === this.formData().key) ??
      null
  )

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
      .find((s) => s.schema_name === this.formData().schema)
      ?.tables.map((table) => ({ value: table, label: table })) ?? [])
  ])

  constructor() {
    effect(() => this.dbDataChanged.emit(this.formData()))
  }

  displayName(db: SourceDatabaseSummary): string {
    return db.label ? `${db.key} ${db.label}` : db.key
  }

  // Schema, table and title belong to the database: cleared when it changes
  select(key: string): void {
    this.formData.set({ ...EMPTY, key })
  }

  selectSchema(schema: string): void {
    this.formData.update((d) => ({ ...d, schema, table: '', title: '' }))
  }

  selectTable(table: string): void {
    this.formData.update((d) => ({ ...d, table, title: '' }))
  }

  setTitle(title: string): void {
    this.formData.update((d) => ({ ...d, title }))
  }
}
