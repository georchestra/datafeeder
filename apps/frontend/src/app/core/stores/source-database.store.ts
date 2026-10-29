import { Injectable, inject, signal } from '@angular/core'
import { Api } from '../api/api'
import { listSourceDatabasesSourceDatabasesGet } from '../api/functions'
import type { SourceDatabaseSummary } from '../api/models'

@Injectable({ providedIn: 'root' })
export class SourceDatabaseStore {
  sourceDatabases = signal<SourceDatabaseSummary[]>([])

  private api = inject(Api)

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

  find(key: string | null | undefined): SourceDatabaseSummary | null {
    return this.sourceDatabases().find((db) => db.key === key) ?? null
  }
}
