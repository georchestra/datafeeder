import { Component, effect, inject, signal } from '@angular/core'
import { DatePipe } from '@angular/common'
import { Router } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs'
import { firstValueFrom } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { MatDialog } from '@angular/material/dialog'
import { ConfirmationDialogComponent } from 'geonetwork-ui'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdDelete,
  listIntegrityLinksIngestionIntegrityLinksGet
} from '../../core/api/functions'
import { IntegrityLinkListItem } from '../../core/api/models'
import {
  iconoirPlus,
  iconoirChatBubbleWarning,
  iconoirTrash,
  iconoirRefreshCircle,
  iconoirEditPencil
} from '@ng-icons/iconoir'
import { SearchInputComponent } from '../../shared/components/search-input/search-input.component'
import { QuickCreationComponent } from '../../shared/components/quick-creation/quick-creation.component'
import { RecurrenceLabelPipe } from '../../shared/pipes/recurrence-label.pipe'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import { EMPTY_IMPORT_TYPE } from '../../core/stores/integrity-link.store'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('integrityLinks.edit')
marker('integrityLinks.visibility.open')
marker('integrityLinks.visibility.restricted')
marker('integrityLinks.visibility.unconfigured')

const DEBOUNCE_TIME = 300

@Component({
  selector: 'app-integrity-link-list',
  imports: [
    DatePipe,
    TranslatePipe,
    NgIconComponent,
    SearchInputComponent,
    QuickCreationComponent,
    RecurrenceLabelPipe
  ],
  templateUrl: './integrity-link-list.component.html',
  providers: [
    provideIcons({
      iconoirPlus,
      iconoirChatBubbleWarning,
      iconoirTrash,
      iconoirRefreshCircle,
      iconoirEditPencil
    })
  ]
})
export class IntegrityLinkListComponent {
  readonly emptyImportType = EMPTY_IMPORT_TYPE

  private api = inject(Api)
  private router = inject(Router)
  private translate = inject(TranslateService)
  private matDialog = inject(MatDialog)
  private operationToastStore = inject(OperationToastStore)

  integrityLinks = signal<IntegrityLinkListItem[]>([])
  loading = signal<boolean>(true)
  hasMore = signal<boolean>(false)
  loadingMore = signal<boolean>(false)
  searchQuery = signal('')
  deleting = signal<string | null>(null)
  private nextOffset = signal(0)

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
    if (!append) {
      this.hasMore.set(false)
      this.nextOffset.set(0)
    }
    try {
      const offset = append ? this.nextOffset() : 0
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
      this.nextOffset.set(response.next_offset)
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

  onEditClick(link: IntegrityLinkListItem): void {
    if (
      !link.has_final_table &&
      link.source_import_type !== EMPTY_IMPORT_TYPE
    ) {
      this.router.navigate(['/', 'import', link.id], {
        queryParams: { step: 2 }
      })
    } else {
      this.router.navigate(['/', link.id, 'edit'])
    }
  }

  getVisibility(
    link: IntegrityLinkListItem
  ): 'open' | 'restricted' | 'unconfigured' {
    if (link.gn_is_published && link.gs_is_published) return 'open'
    if (
      link.gn_is_published ||
      link.gs_is_published ||
      link.has_integrity_rules
    )
      return 'restricted'
    return 'unconfigured'
  }

  isReadOnly(link: IntegrityLinkListItem): boolean {
    return link.access_level === 'READ'
  }

  canDelete(link: IntegrityLinkListItem): boolean {
    return link.access_level === 'OWNER' || link.access_level === 'ADMIN'
  }

  async deleteIntegrityLink(event: Event, id: string): Promise<void> {
    ;(event.currentTarget as HTMLElement)?.blur()
    if (this.deleting()) return
    const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
      data: {
        title: this.translate.instant('dashboard.deleteDataset'),
        message: this.translate.instant('dashboard.deleteDatasetConfirm'),
        confirmText: this.translate.instant('common.delete'),
        cancelText: this.translate.instant('common.cancel'),
        focusCancel: 'cancel'
      }
    })
    const confirmed = await firstValueFrom(dialogRef.afterClosed())
    if (!confirmed) return
    this.deleting.set(id)
    try {
      await this.api.invoke(
        deleteIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdDelete,
        { integrity_link_id: id }
      )
      this.integrityLinks.update((items) => items.filter((l) => l.id !== id))
    } catch (error) {
      console.error('Failed to delete integrity link:', error)
      this.operationToastStore.addError('deletion')
    } finally {
      this.deleting.set(null)
    }
  }
}
