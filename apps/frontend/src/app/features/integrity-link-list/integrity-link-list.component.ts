import { Component, inject, signal } from '@angular/core'
import { DatePipe } from '@angular/common'
import { Router } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { listIntegrityLinksIngestionIntegrityLinksGet } from '../../core/api/functions'
import { IntegrityLinkListItem } from '../../core/api/models'

@Component({
  selector: 'app-integrity-link-list',
  imports: [DatePipe, TranslatePipe],
  templateUrl: './integrity-link-list.component.html'
})
export class IntegrityLinkListComponent {
  private api = inject(Api)
  private router = inject(Router)

  integrityLinks = signal<IntegrityLinkListItem[]>([])
  loading = signal<boolean>(true)
  hasMore = signal<boolean>(false)
  loadingMore = signal<boolean>(false)

  constructor() {
    this.loadIntegrityLinks()
  }

  private async loadIntegrityLinks(append = false): Promise<void> {
    try {
      const offset = append ? this.integrityLinks().length : 0
      const response = await this.api.invoke(
        listIntegrityLinksIngestionIntegrityLinksGet,
        { offset }
      )
      if (append) {
        this.integrityLinks.update((items) => [...items, ...response.items])
      } else {
        this.integrityLinks.set(response.items)
      }
      this.hasMore.set(response.has_more)
    } catch (error) {
      console.error('Failed to load integrity links:', error)
    } finally {
      this.loading.set(false)
      this.loadingMore.set(false)
    }
  }

  loadMore(): void {
    this.loadingMore.set(true)
    this.loadIntegrityLinks(true)
  }

  onRowClick(id: string): void {
    this.router.navigate(['/edit', id])
  }
}
