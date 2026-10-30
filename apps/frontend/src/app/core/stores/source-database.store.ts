import { Injectable, inject, signal } from '@angular/core'
import { Api } from '../api/api'
import {
  listSourceDatabasesSourceDatabasesGet,
  listSourceDatabaseTablesSourceDatabasesKeyTablesGet
} from '../api/functions'
import type { SourceDatabaseSummary, SourceSchema } from '../api/models'

@Injectable({ providedIn: 'root' })
export class SourceDatabaseStore {
  sourceDatabases = signal<SourceDatabaseSummary[]>([])
  schemas = signal<SourceSchema[]>([])

  private api = inject(Api)
  private schemasKey = ''

  async load(): Promise<void> {
    try {
      this.sourceDatabases.set(
        await this.api.invoke(listSourceDatabasesSourceDatabasesGet)
      )
    } catch {
      // Admin-only endpoint for now: other users get an empty list
      this.sourceDatabases.set([])
    }
  }

  async loadSchemas(key: string): Promise<void> {
    this.schemasKey = key
    this.schemas.set([])
    if (!key) return
    const schemas = await this.api
      .invoke(listSourceDatabaseTablesSourceDatabasesKeyTablesGet, { key })
      .catch(() => [])
    // A response for a previously selected database is dropped
    if (key === this.schemasKey) this.schemas.set(schemas)
  }

  find(key: string | null | undefined): SourceDatabaseSummary | null {
    return this.sourceDatabases().find((db) => db.key === key) ?? null
  }
}
