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

  constructor() {
    this.loadIntegrityLinks()
  }

  private async loadIntegrityLinks(): Promise<void> {
    try {
      const response = await this.api.invoke(
        listIntegrityLinksIngestionIntegrityLinksGet
      )
      this.integrityLinks.set(response.items)
    } catch (error) {
      console.error('Failed to load integrity links:', error)
    } finally {
      this.loading.set(false)
    }
  }

  onRowClick(id: string): void {
    this.router.navigate(['/edit', id])
  }
}
