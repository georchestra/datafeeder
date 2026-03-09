import { Component, effect, inject, signal } from '@angular/core'
import { DatePipe } from '@angular/common'
import { Router } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { TranslatePipe } from '@ngx-translate/core'
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Api } from '../../core/api/api'
import { listIntegrityLinksIngestionIntegrityLinksGet } from '../../core/api/functions'
import { IntegrityLinkListItem } from '../../core/api/models'
import { iconoirPlus, iconoirChatBubbleWarning } from '@ng-icons/iconoir'
import { SearchInputComponent } from '../../shared/components/search-input/search-input.component'

const DEBOUNCE_TIME = 300

@Component({
  selector: 'app-integrity-link-list',
  imports: [DatePipe, TranslatePipe, NgIconComponent, SearchInputComponent],
  templateUrl: './integrity-link-list.component.html',
  providers: [
    provideIcons({
      iconoirPlus,
      iconoirChatBubbleWarning
    })
  ]
})
export class IntegrityLinkListComponent {
  private api = inject(Api)
  private router = inject(Router)

  integrityLinks = signal<IntegrityLinkListItem[]>([])
  loading = signal<boolean>(true)
  hasMore = signal<boolean>(false)
  loadingMore = signal<boolean>(false)
  searchQuery = signal('')

  private searchSubject = new Subject<string>()

  constructor() {
    effect(() => {
      this.searchSubject.next(this.searchQuery())
    })
    this.searchSubject
      .pipe(
        debounceTime(DEBOUNCE_TIME),
        distinctUntilChanged(),
        takeUntilDestroyed()
      )
      .subscribe(() => {
        this.loading.set(true)
        this.loadIntegrityLinks()
      })
    this.loadIntegrityLinks()
  }

  private async loadIntegrityLinks(append = false): Promise<void> {
    try {
      const offset = append ? this.integrityLinks().length : 0
      const search = this.searchQuery() || undefined
      const response = await this.api.invoke(
        listIntegrityLinksIngestionIntegrityLinksGet,
        { offset, search }
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

  onRowClick(link: IntegrityLinkListItem): void {
    if (link.access_level === 'READ') return
    if (!link.has_final_table) {
      this.router.navigate(['/', 'import', link.id], { queryParams: { step: 2 } })
    } else {
      this.router.navigate(['/', link.id, 'edit'])
    }
  }

  isReadOnly(link: IntegrityLinkListItem): boolean {
    return link.access_level === 'READ'
  }
}
