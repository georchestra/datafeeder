/**
 * Vitest unit tests for RecurrenceComponent.
 *
 * Covers preset initialization from the store, preset loading, and the
 * schedule PATCH triggered by onPresetChange (with EVERY_MINUTE confirmation).
 */

import { Component, Input } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { of } from 'rxjs'
import { Api } from '../../core/api/api'
import {
  listRecurrencePresetsIngestionRecurrencePresetsGet,
  updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch
} from '../../core/api/functions'
import type { IntegrityLinkResponse } from '../../core/api/models/integrity-link-response'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import { RecurrenceSelectorComponent } from '../../shared/components/recurrence-selector/recurrence-selector.component'
import { RecurrenceComponent } from './recurrence.component'

// ─── Stub child component to avoid its transitive dependencies ──────────────

@Component({
  selector: 'app-recurrence-selector',
  standalone: true,
  template: ''
})
class MockRecurrenceSelectorComponent {
  @Input() presets: unknown[] = []
  @Input() selectedPresetId: string | null = null
  @Input() currentRecurrence: unknown = null
  @Input() disabled: boolean = false
}

// ─── Test helpers ────────────────────────────────────────────────────────────

const makeIntegrityLink = (
  overrides: Partial<IntegrityLinkResponse> = {}
): IntegrityLinkResponse =>
  ({
    id: 'test-intlink-id',
    data_id: null,
    metadata_id: null,
    integrity_title: null,
    integrity_owner: 'testuser',
    integrity_organization: 'testorg',
    source_import_type: 'url',
    source_url: 'http://example.com/data.geojson',
    source_file_name: null,
    source_file_type: null,
    source_username: null,
    staging_table_name: 'staging_test',
    staging_retrieve_time: null,
    final_table_name: null,
    last_retrieval_timestamp: null,
    schedule: null,
    schedule_enabled: false,
    preset_id: null,
    created_at: null,
    gn_is_published: null,
    ...overrides
  } as IntegrityLinkResponse)

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('RecurrenceComponent', () => {
  const intlinkId = 'test-intlink-id'

  let apiInvokeSpy: ReturnType<typeof vi.fn>
  let dialogOpenSpy: ReturnType<typeof vi.fn>
  let dialogResult: boolean
  let store: IntegrityLinkStore
  let toastStore: OperationToastStore

  beforeEach(async () => {
    apiInvokeSpy = vi.fn().mockResolvedValue([])
    dialogResult = true
    dialogOpenSpy = vi.fn(() => ({ afterClosed: () => of(dialogResult) }))

    await TestBed.configureTestingModule({
      imports: [
        RecurrenceComponent,
        TranslateTestingModule.withTranslations({ en: {} })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        IntegrityLinkStore,
        { provide: Api, useValue: { invoke: apiInvokeSpy } },
        { provide: MatDialog, useValue: { open: dialogOpenSpy } }
      ]
    })
      .overrideComponent(RecurrenceComponent, {
        remove: { imports: [RecurrenceSelectorComponent] },
        add: { imports: [MockRecurrenceSelectorComponent] }
      })
      .compileComponents()

    store = TestBed.inject(IntegrityLinkStore)
    toastStore = TestBed.inject(OperationToastStore)
    store.intlinkId.set(intlinkId)
  })

  const createComponent = () => {
    const fixture = TestBed.createComponent(RecurrenceComponent)
    fixture.detectChanges()
    return { fixture, component: fixture.componentInstance }
  }

  // ─── Recurrence display ──────────────────────────────────────────────────

  describe('Recurrence display', () => {
    it('should initialize selectedPresetId from store when schedule is enabled', () => {
      store.integrityLink.set(
        makeIntegrityLink({ preset_id: 'EVERY_DAY', schedule_enabled: true })
      )

      const { component } = createComponent()

      expect(component.selectedPresetId()).toBe('EVERY_DAY')
    })

    it('should initialize selectedPresetId to null when preset_id is null', () => {
      store.integrityLink.set(
        makeIntegrityLink({ preset_id: null, schedule_enabled: true })
      )

      const { component } = createComponent()

      expect(component.selectedPresetId()).toBeNull()
    })

    it('should initialize selectedPresetId to null when integrityLink is not loaded', () => {
      store.integrityLink.set(null)

      const { component } = createComponent()

      expect(component.selectedPresetId()).toBeNull()
    })

    it('should initialize selectedPresetId to null when schedule_enabled is false', () => {
      store.integrityLink.set(
        makeIntegrityLink({ preset_id: 'EVERY_DAY', schedule_enabled: false })
      )

      const { component } = createComponent()

      expect(component.selectedPresetId()).toBeNull()
    })
  })

  // ─── Preset loading ──────────────────────────────────────────────────────

  describe('Preset loading', () => {
    it('should add a toast when preset fetch fails', async () => {
      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (fn === listRecurrencePresetsIngestionRecurrencePresetsGet)
          return Promise.reject(new Error('Fetch failed'))
        return Promise.resolve(null)
      })

      createComponent()

      await vi.waitFor(() => expect(toastStore.toasts().length).toBe(1))
      expect(toastStore.toasts()[0].translationKey).toBe(
        'errors.operation.loadPresets'
      )
    })
  })

  // ─── Schedule update ─────────────────────────────────────────────────────

  describe('Schedule update', () => {
    it('should NOT call PATCH /schedule on component init', async () => {
      createComponent()

      await new Promise((r) => setTimeout(r, 20))

      expect(apiInvokeSpy).not.toHaveBeenCalledWith(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        expect.anything()
      )
    })

    it('should call PATCH /schedule when a preset is selected', async () => {
      const { component } = createComponent()

      await component.onPresetChange('EVERY_DAY')

      expect(apiInvokeSpy).toHaveBeenCalledWith(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        {
          integrity_link_id: intlinkId,
          body: { preset: 'EVERY_DAY' }
        }
      )
    })

    it('should NOT call PATCH /schedule when intlink_id is null', async () => {
      store.intlinkId.set(null)
      const { component } = createComponent()

      await component.onPresetChange('EVERY_DAY')

      expect(apiInvokeSpy).not.toHaveBeenCalledWith(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        expect.anything()
      )
    })

    it('should update the store with preset_id, schedule and schedule_enabled from the response', async () => {
      store.integrityLink.set(
        makeIntegrityLink({
          preset_id: null,
          schedule: null,
          schedule_enabled: false
        })
      )
      const { component } = createComponent()

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch
        ) {
          return Promise.resolve(
            makeIntegrityLink({
              preset_id: 'EVERY_DAY',
              schedule: '0 0 * * *',
              schedule_enabled: true
            })
          )
        }
        return Promise.resolve([])
      })

      await component.onPresetChange('EVERY_DAY')

      expect(store.integrityLink()?.preset_id).toBe('EVERY_DAY')
      expect(store.integrityLink()?.schedule).toBe('0 0 * * *')
      expect(store.integrityLink()?.schedule_enabled).toBe(true)
    })

    it('should add an error toast when PATCH /schedule fails', async () => {
      const { component } = createComponent()

      apiInvokeSpy.mockImplementation((fn: unknown) => {
        if (
          fn ===
          updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch
        ) {
          return Promise.reject(new Error('Network error'))
        }
        return Promise.resolve([])
      })

      await component.onPresetChange('EVERY_DAY')

      expect(toastStore.toasts().length).toBeGreaterThan(0)
    })
  })

  // ─── EVERY_MINUTE confirmation ───────────────────────────────────────────

  describe('EVERY_MINUTE confirmation', () => {
    it('should NOT open a dialog for other presets', async () => {
      const { component } = createComponent()

      await component.onPresetChange('EVERY_DAY')

      expect(dialogOpenSpy).not.toHaveBeenCalled()
    })

    it('should open a confirmation dialog and PATCH when confirmed', async () => {
      dialogResult = true
      const { component } = createComponent()

      await component.onPresetChange('EVERY_MINUTE')

      expect(dialogOpenSpy).toHaveBeenCalled()
      expect(component.selectedPresetId()).toBe('EVERY_MINUTE')
      expect(apiInvokeSpy).toHaveBeenCalledWith(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        {
          integrity_link_id: intlinkId,
          body: { preset: 'EVERY_MINUTE' }
        }
      )
    })

    it('should revert to the previous preset and NOT PATCH when cancelled', async () => {
      store.integrityLink.set(
        makeIntegrityLink({ preset_id: 'EVERY_DAY', schedule_enabled: true })
      )
      dialogResult = false
      const { component } = createComponent()

      await component.onPresetChange('EVERY_MINUTE')

      expect(dialogOpenSpy).toHaveBeenCalled()
      expect(component.selectedPresetId()).toBe('EVERY_DAY')
      expect(apiInvokeSpy).not.toHaveBeenCalledWith(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        expect.anything()
      )
    })
  })
})
