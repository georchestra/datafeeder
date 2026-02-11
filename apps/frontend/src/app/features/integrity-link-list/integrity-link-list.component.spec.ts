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
  const createMockItem = (id: string): IntegrityLinkListItem => ({
    id,
    integrity_title: `Link ${id}`,
    integrity_owner: 'owner',
    integrity_organization: 'org',
    source_import_type: 'url',
    staging_table_name: `staging_${id}`,
    source_url: 'https://example.com/data.csv',
    source_file_name: null,
    source_file_type: null,
    source_auth_enabled: false,
    created_at: '2024-01-01T00:00:00Z',
    last_retrieval_timestamp: null,
    schedule: null,
    schedule_enabled: false,
    data_id: null,
    metadata_id: null,
    final_table_name: null
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
            'integrityLinks.noItems': 'No items'
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
    it('should navigate to /edit/:id when onRowClick(id) is called', async () => {
      const fixture = TestBed.createComponent(IntegrityLinkListComponent)
      const component = fixture.componentInstance

      const navigateSpy = vi.spyOn(router, 'navigate')

      // Complete initial load
      const req = httpMock.expectOne(
        'http://localhost:8000/ingestion/integrity-links/?offset=0'
      )
      req.flush({
        items: [createMockItem('test-id-123')],
        has_more: false,
        offset: 0
      })

      await new Promise((resolve) => setTimeout(resolve, 10))

      // Trigger row click
      component.onRowClick('test-id-123')

      expect(navigateSpy).toHaveBeenCalledWith(['/', 'test-id-123', 'edit'])
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
})
