import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { ApiConfiguration } from '../../core/api/api-configuration'
import { IntegrityLinkListItem } from '../../core/api/models'
import { IntegrityLinkListComponent } from './integrity-link-list.component'

describe('IntegrityLinkListComponent', () => {
  let httpMock: HttpTestingController
  let router: Router

  // Mock data helper function
  const createMockItem = (
    id: string,
    accessLevel: string | null = 'OWNER',
    hasFinalTable: boolean = true
  ): IntegrityLinkListItem => ({
    id,
    integrity_title: `Link ${id}`,
    integrity_owner: 'owner',
    integrity_organization: 'org',
    source_import_type: 'url',
    staging_table_name: `staging_${id}`,
    source_url: 'https://example.com/data.csv',
    source_file_name: null,
    source_file_type: null,
    created_at: '2024-01-01T00:00:00Z',
    last_retrieval_timestamp: null,
    schedule: null,
    schedule_enabled: false,
    data_id: null,
    metadata_id: null,
    final_table_name: hasFinalTable ? `final_${id}` : null,
    has_final_table: hasFinalTable,
    access_level: accessLevel
  })

  // Helper to flush pending requests
  const flushPendingRequests = () => {
    const pendingRequests = httpMock.match(() => true)
    pendingRequests.forEach((req) => {
      if (!req.cancelled) {
        req.flush({ items: [], has_more: false, offset: 0 })
      }
    })
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        IntegrityLinkListComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'integrityLinks.title': 'Integrity Links',
            'integrityLinks.loadMore': 'Load More',
            'integrityLinks.noItems': 'No items',
            'dashboard.delete_dataset': 'Delete dataset',
            'dashboard.delete_dataset_confirm': 'Are you sure?'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
    router = TestBed.inject(Router)
  })

  afterEach(() => {
    flushPendingRequests()
    httpMock.verify()
  })

  describe('Initial Load', () => {
    it('should load integrity links on component init', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      expect(component.loading()).toBe(true)

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      expect(req.request.method).toBe('GET')

      req.flush({
        items: [createMockItem('1'), createMockItem('2')],
        has_more: true,
        offset: 0
      })

      // Wait for promise to resolve
      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.integrityLinks().length).toBe(2)
      expect(component.integrityLinks()[0].id).toBe('1')
    })

    it('should set loading to false after load completes', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      expect(component.loading()).toBe(true)

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.loading()).toBe(false)
    })

    it('should update hasMore from API response', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )

      req.flush({
        items: [createMockItem('1')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.hasMore()).toBe(true)
    })

    it('should set hasMore to false when no more items', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )

      req.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.hasMore()).toBe(false)
    })
  })

  describe('Load More Pagination', () => {
    it('should append items when loadMore() is called', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1'), createMockItem('2')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.integrityLinks().length).toBe(2)

      // Call loadMore
      component.loadMore()

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=2'
      )
      loadMoreReq.flush({
        items: [createMockItem('3'), createMockItem('4')],
        has_more: false,
        offset: 2
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Items should be appended, not replaced
      expect(component.integrityLinks().length).toBe(4)
      expect(component.integrityLinks()[0].id).toBe('1')
      expect(component.integrityLinks()[2].id).toBe('3')
    })

    it('should pass correct offset parameter to API', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load with 3 items
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1'), createMockItem('2'), createMockItem('3')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Call loadMore - offset should be 3 (current items count)
      component.loadMore()

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=3'
      )
      expect(loadMoreReq.request.params.get('offset')).toBe('3')

      loadMoreReq.flush({
        items: [createMockItem('4')],
        has_more: false,
        offset: 3
      })
    })

    it('should set loadingMore to true during load, false after', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.loadingMore()).toBe(false)

      // Call loadMore
      component.loadMore()

      // loadingMore should be true immediately
      expect(component.loadingMore()).toBe(true)

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=1'
      )
      loadMoreReq.flush({
        items: [createMockItem('2')],
        has_more: false,
        offset: 1
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.loadingMore()).toBe(false)
    })
  })

  describe('Navigation', () => {
    it('should navigate to /edit/:id when onRowClick is called with writable link', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const navigateSpy = vi.spyOn(router, 'navigate')

      // Complete initial load
      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('test-id-123', 'OWNER')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Trigger row click with writable link
      component.onRowClick(createMockItem('test-id-123', 'OWNER'))

      expect(navigateSpy).toHaveBeenCalledWith(['/', 'test-id-123', 'edit'])
    })

    it('should NOT navigate when onRowClick is called with READ-only link', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const navigateSpy = vi.spyOn(router, 'navigate')

      // Complete initial load
      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('read-only-id', 'READ')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Trigger row click with read-only link
      component.onRowClick(createMockItem('read-only-id', 'READ'))

      expect(navigateSpy).not.toHaveBeenCalled()
    })

    it('should identify read-only links correctly', () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      flushPendingRequests()

      expect(component.isReadOnly(createMockItem('1', 'READ'))).toBe(true)
      expect(component.isReadOnly(createMockItem('2', 'WRITE'))).toBe(false)
      expect(component.isReadOnly(createMockItem('3', 'OWNER'))).toBe(false)
      expect(component.isReadOnly(createMockItem('4', 'ADMIN'))).toBe(false)
      expect(component.isReadOnly(createMockItem('5', null))).toBe(false)
    })

    it('should navigate to /:id/edit when link has has_final_table=true', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance
      const navigateSpy = vi.spyOn(router, 'navigate')

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('link-42')],
        has_more: false,
        offset: 0
      })
      await new Promise((resolve) => setTimeout(resolve, 10))

      component.onRowClick(createMockItem('link-42', 'OWNER', true))

      expect(navigateSpy).toHaveBeenCalledWith(['/', 'link-42', 'edit'])
    })

    it('should navigate to /import/:id with step=2 when link has no final table', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance
      const navigateSpy = vi.spyOn(router, 'navigate')

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('link-42')],
        has_more: false,
        offset: 0
      })
      await new Promise((resolve) => setTimeout(resolve, 10))

      component.onRowClick(createMockItem('link-42', 'OWNER', false))

      expect(navigateSpy).toHaveBeenCalledWith(['/', 'import', 'link-42'], {
        queryParams: { step: 2 }
      })
    })
  })

  describe('Search', () => {
    it('should trigger debounced API call with search param', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Trigger search
      component.searchQuery.set('test')
      fixture.detectChanges()

      // Wait for debounce (300ms)
      await new Promise((resolve) => setTimeout(resolve, 350))

      const searchReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0&search=test'
      )
      expect(searchReq.request.method).toBe('GET')
      expect(searchReq.request.params.get('search')).toBe('test')

      searchReq.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })
    })

    it('should reset search and reload when clearSearch is called', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Set a search first
      component.searchQuery.set('test')
      fixture.detectChanges()
      await new Promise((resolve) => setTimeout(resolve, 350))

      const searchReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0&search=test'
      )
      searchReq.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Clear search
      component.searchQuery.set('')
      fixture.detectChanges()

      expect(component.searchQuery()).toBe('')

      await new Promise((resolve) => setTimeout(resolve, 350))

      const clearReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      expect(clearReq.request.params.has('search')).toBe(false)

      clearReq.flush({
        items: [createMockItem('1'), createMockItem('2')],
        has_more: false,
        offset: 0
      })
    })

    it('should include search param when loading more', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Set search
      component.searchQuery.set('test')
      fixture.detectChanges()
      await new Promise((resolve) => setTimeout(resolve, 350))

      const searchReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0&search=test'
      )
      searchReq.flush({
        items: [createMockItem('a')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Load more with search active
      component.loadMore()

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=1&search=test'
      )
      expect(loadMoreReq.request.params.get('offset')).toBe('1')
      expect(loadMoreReq.request.params.get('search')).toBe('test')

      loadMoreReq.flush({
        items: [createMockItem('b')],
        has_more: false,
        offset: 1
      })
    })

    it('should not include search param when search is empty', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      expect(req.request.params.has('search')).toBe(false)

      req.flush({
        items: [createMockItem('1')],
        has_more: false,
        offset: 0
      })
    })
  })

  describe('Error Handling', () => {
    it('should set loading flags to false even on API error', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      expect(component.loading()).toBe(true)

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )

      // Simulate a network error
      req.error(new ProgressEvent('Network error'), {
        status: 500,
        statusText: 'Server Error'
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Loading should be false even after error
      expect(component.loading()).toBe(false)
    })

    it('should set loadingMore to false on error during pagination', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Call loadMore
      component.loadMore()

      expect(component.loadingMore()).toBe(true)

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=1'
      )

      // Simulate error
      loadMoreReq.error(new ProgressEvent('Network error'), {
        status: 500,
        statusText: 'Server Error'
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.loadingMore()).toBe(false)
    })

    it('should preserve existing items on loadMore error', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      // Initial load
      const initialReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      initialReq.flush({
        items: [createMockItem('1'), createMockItem('2')],
        has_more: true,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.integrityLinks().length).toBe(2)

      // Call loadMore
      component.loadMore()

      const loadMoreReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=2'
      )

      // Simulate error
      loadMoreReq.error(new ProgressEvent('Network error'), {
        status: 500,
        statusText: 'Server Error'
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Existing items should be preserved
      expect(component.integrityLinks().length).toBe(2)
      expect(component.integrityLinks()[0].id).toBe('1')
    })
  })

  describe('Delete Dataset', () => {
    const setupWithItems = async (items: IntegrityLinkListItem[]) => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({ items, has_more: false, offset: 0 })

      await new Promise((resolve) => setTimeout(resolve, 10))
      return { fixture, component }
    }

    it('should hide trash icon by default (hoveredId is null)', async () => {
      const { component } = await setupWithItems([createMockItem('1')])
      expect(component.hoveredId()).toBeNull()
    })

    it('should show trash icon when hoveredId matches row id', async () => {
      const { component } = await setupWithItems([createMockItem('1')])
      component.hoveredId.set('1')
      expect(component.hoveredId()).toBe('1')
    })

    it('should call DELETE API on deleteIntegrityLink when confirmed', async () => {
      const { component } = await setupWithItems([
        createMockItem('1'),
        createMockItem('2')
      ])

      vi.spyOn(window, 'confirm').mockReturnValue(true)

      const event = new MouseEvent('click')
      vi.spyOn(event, 'stopPropagation')

      component.deleteIntegrityLink(event, '1')

      expect(event.stopPropagation).toHaveBeenCalled()

      const deleteReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/1'
      )
      expect(deleteReq.request.method).toBe('DELETE')
      deleteReq.flush(null, { status: 204, statusText: 'No Content' })

      await new Promise((resolve) => setTimeout(resolve, 10))
    })

    it('should remove item from list on successful delete (204)', async () => {
      const { component } = await setupWithItems([
        createMockItem('1'),
        createMockItem('2')
      ])

      expect(component.integrityLinks().length).toBe(2)

      vi.spyOn(window, 'confirm').mockReturnValue(true)

      component.deleteIntegrityLink(new MouseEvent('click'), '1')

      const deleteReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/1'
      )
      deleteReq.flush(null, { status: 204, statusText: 'No Content' })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.integrityLinks().length).toBe(1)
      expect(component.integrityLinks()[0].id).toBe('2')
    })

    it('should NOT remove item from list on API failure', async () => {
      const { component } = await setupWithItems([
        createMockItem('1'),
        createMockItem('2')
      ])

      expect(component.integrityLinks().length).toBe(2)

      vi.spyOn(window, 'confirm').mockReturnValue(true)

      component.deleteIntegrityLink(new MouseEvent('click'), '1')

      const deleteReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/1'
      )
      deleteReq.error(new ProgressEvent('Network error'), {
        status: 500,
        statusText: 'Server Error'
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.integrityLinks().length).toBe(2)
    })

    it('should NOT call API when user cancels confirm dialog', async () => {
      const { component } = await setupWithItems([createMockItem('1')])

      vi.spyOn(window, 'confirm').mockReturnValue(false)

      component.deleteIntegrityLink(new MouseEvent('click'), '1')

      httpMock.expectNone('http://localhost:8000/ingestion/integrity-link/1')

      expect(component.integrityLinks().length).toBe(1)
    })

    it('should reset deleting signal after completion', async () => {
      const { component } = await setupWithItems([createMockItem('1')])

      vi.spyOn(window, 'confirm').mockReturnValue(true)

      component.deleteIntegrityLink(new MouseEvent('click'), '1')

      const deleteReq = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-link/1'
      )
      deleteReq.flush(null, { status: 204, statusText: 'No Content' })

      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(component.deleting()).toBeNull()
    })
  })
})
