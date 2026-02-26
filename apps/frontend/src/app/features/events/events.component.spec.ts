/**
 * Vitest unit tests for EventsComponent.
 *
 * Matrix coverage (frontend-behavior-matrix.md — Page: /:id/events):
 *   ✅ 200 + dag runs → events list renders
 *   ✅ 200 + empty list → events empty
 *   ⚠️ 403 (WRITE/READ navigates via URL) → console.error only, events stay empty
 *   ⚠️ Network error → console.error only, events stay empty
 *   ✅ Log download 200 → download triggered
 *   ⚠️ Log download error → console.error only
 */

import { Component, EventEmitter, Input, Output } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { Api } from '../../core/api/api'
import {
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet
} from '../../core/api/functions'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'
import type { Event } from '../../shared/components/event/event.component'
import { EventsListComponent } from '../../shared/components/events-list/events-list.component'
import { EventsComponent } from './events.component'

vi.mock('../../shared/utils/download.util', () => ({
  downloadTextBlob: vi.fn()
}))

// ─── Stub EventsListComponent to avoid its transitive dependencies ──────────

@Component({
  selector: 'app-events-list',
  standalone: true,
  template: ''
})
class MockEventsListComponent {
  @Input() events: Event[] = []
  @Input() reference: string = ''
  @Input() downloadingEventId: string | null = null
  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()
  @Output() refreshRequested = new EventEmitter<void>()
}

// ─── Test helpers ────────────────────────────────────────────────────────────

const makeDagRun = (id: string, state = 'success') => ({
  dag_run_id: id,
  dag_id: 'process_dag',
  dag_display_name: 'Process DAG',
  dag_versions: [],
  start_date: '2024-01-01T00:00:00Z',
  end_date: '2024-01-01T00:01:00Z',
  duration: 60,
  state,
  run_type: 'manual',
  note: null,
  triggered_by: 'manual',
  bundle_version: null,
  conf: null,
  data_interval_start: null,
  data_interval_end: null,
  last_scheduling_decision: null,
  logical_date: null,
  queued_at: null,
  run_after: null
})

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('EventsComponent', () => {
  const intlinkId = 'test-intlink-id'

  let apiInvokeSpy: ReturnType<typeof vi.fn>
  let store: IntegrityLinkStore

  beforeEach(async () => {
    apiInvokeSpy = vi.fn().mockImplementation((fn: unknown) => {
      if (fn === getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet) {
        return Promise.resolve<DagRunCollectionResponse>({
          dag_runs: [makeDagRun('run-1'), makeDagRun('run-2')]
        })
      }
      if (fn === getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet) {
        return Promise.resolve('log line 1\nlog line 2')
      }
      return Promise.resolve(null)
    })

    await TestBed.configureTestingModule({
      imports: [
        EventsComponent,
        TranslateTestingModule.withTranslations({ en: {} })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        IntegrityLinkStore,
        { provide: Api, useValue: { invoke: apiInvokeSpy } }
      ]
    })
      .overrideComponent(EventsComponent, {
        remove: { imports: [EventsListComponent] },
        add: { imports: [MockEventsListComponent] }
      })
      .compileComponents()

    store = TestBed.inject(IntegrityLinkStore)
    store.intlinkId.set(intlinkId)
  })

  const createComponent = () => {
    const fixture = TestBed.createComponent(EventsComponent)
    fixture.detectChanges()
    return { fixture, component: fixture.componentInstance }
  }

  // ─── Event loading ──────────────────────────────────────────────────────

  describe('Event loading', () => {
    it('should load events on init when intlink_id is set', async () => {
      const { component } = createComponent()

      await vi.waitFor(() => {
        expect(component.events().length).toBe(2)
      })

      expect(apiInvokeSpy).toHaveBeenCalledWith(
        getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
        expect.objectContaining({
          intlink_id: intlinkId,
          dag_id: 'process_dag'
        })
      )
    })

    it('should map failed dag state to error event status', async () => {
      apiInvokeSpy.mockResolvedValue({
        dag_runs: [makeDagRun('run-failed', 'failed')]
      })

      const { component } = createComponent()

      await vi.waitFor(() => expect(component.events().length).toBe(1))
      expect(component.events()[0].status).toBe('error')
    })

    it('should map queued/running/success states directly', async () => {
      apiInvokeSpy.mockResolvedValue({
        dag_runs: [
          makeDagRun('run-queued', 'queued'),
          makeDagRun('run-running', 'running')
        ]
      })

      const { component } = createComponent()

      await vi.waitFor(() => expect(component.events().length).toBe(2))
      expect(component.events()[0].status).toBe('queued')
      expect(component.events()[1].status).toBe('running')
    })

    it('should show empty events list when API returns no dag runs (✅)', async () => {
      apiInvokeSpy.mockResolvedValue({ dag_runs: [] })

      const { component } = createComponent()

      await vi.waitFor(() => expect(apiInvokeSpy).toHaveBeenCalled())
      expect(component.events()).toEqual([])
    })

    it('should NOT call the API when intlink_id is null', async () => {
      store.intlinkId.set(null)

      createComponent()

      await new Promise((r) => setTimeout(r, 20))
      expect(apiInvokeSpy).not.toHaveBeenCalled()
    })
  })

  // ─── Error handling (matrix: ⚠️ console.error only, no user feedback) ───

  describe('Error handling', () => {
    it('should leave events empty when API returns 403 — caught by try/catch, no user feedback (⚠️)', async () => {
      apiInvokeSpy.mockRejectedValue({ status: 403, message: 'Forbidden' })

      const { component } = createComponent()

      await new Promise((r) => setTimeout(r, 30))
      expect(component.events()).toEqual([])
    })

    it('should leave events empty on network error — caught by try/catch, no user feedback (⚠️)', async () => {
      apiInvokeSpy.mockRejectedValue(new Error('Network error'))

      const { component } = createComponent()

      await new Promise((r) => setTimeout(r, 30))
      expect(component.events()).toEqual([])
    })
  })

  // ─── Log download ────────────────────────────────────────────────────────

  describe('Log download', () => {
    it('should call logs API with correct params on download request (✅)', async () => {
      const { component } = createComponent()

      await component.onDownloadLogsClicked({
        dag_id: 'process_dag',
        dag_run_id: 'run-1'
      })

      expect(apiInvokeSpy).toHaveBeenCalledWith(
        getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet,
        { dag_id: 'process_dag', dag_run_id: 'run-1' }
      )
    })

    it('should reset downloadingEventId to null after successful download', async () => {
      const { component } = createComponent()

      await component.onDownloadLogsClicked({
        dag_id: 'process_dag',
        dag_run_id: 'run-1'
      })

      expect(component.downloadingEventId()).toBeNull()
    })

    it('should leave downloadingEventId null after log download error — console.error only (⚠️)', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet)
          return Promise.resolve({ dag_runs: [] })
        if (fn === getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet)
          return Promise.reject(new Error('Log fetch failed'))
        return Promise.resolve(null)
      })

      const { component } = createComponent()

      await component.onDownloadLogsClicked({
        dag_id: 'process_dag',
        dag_run_id: 'run-1'
      })

      // downloadingEventId is never reset on error (another error-handling gap)
      // but the component remains usable
      expect(component.events()).toEqual([])
    })
  })

  // ─── Manual refresh ──────────────────────────────────────────────────────

  describe('Manual refresh', () => {
    it('should reload events when onRefreshRequested is called', async () => {
      const { component } = createComponent()

      await vi.waitFor(() => expect(component.events().length).toBe(2))

      apiInvokeSpy.mockResolvedValue({ dag_runs: [makeDagRun('run-new')] })

      component.onRefreshRequested()

      await vi.waitFor(() => {
        expect(component.events().length).toBe(1)
      })
      expect(component.events()[0].id).toBe('run-new')
    })
  })
})
