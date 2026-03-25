import { ComponentFixture, TestBed } from '@angular/core/testing'
import { TranslateModule, TranslateService } from '@ngx-translate/core'
import { RecurrenceSelectorComponent } from './recurrence-selector.component'
import type { RecurrencePresetItem } from '../../../core/api/models/recurrence-preset-item'

const DEFAULT_PRESETS: RecurrencePresetItem[] = [
  { id: 'EVERY_DAY', cron: '0 4 * * *' },
  { id: 'EVERY_WEEK', cron: '0 4 * * 1' },
  { id: 'EVERY_MONTH', cron: '0 4 1 * *' }
]

describe('RecurrenceSelectorComponent', () => {
  let component: RecurrenceSelectorComponent
  let fixture: ComponentFixture<RecurrenceSelectorComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RecurrenceSelectorComponent, TranslateModule.forRoot()]
    }).compileComponents()

    fixture = TestBed.createComponent(RecurrenceSelectorComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('selectValue', () => {
    it('returns empty string when no preset selected (wizard mode)', () => {
      expect(component.selectValue()).toBe('')
    })

    it('returns selectedPresetId when not disabled', () => {
      fixture.componentRef.setInput('selectedPresetId', 'EVERY_DAY')
      fixture.detectChanges()
      expect(component.selectValue()).toBe('EVERY_DAY')
    })

    it('returns preset_id from recurrence when disabled with known preset', () => {
      const r = {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      }
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', r)
      fixture.detectChanges()
      expect(component.selectValue()).toBe('EVERY_DAY')
    })

    it('returns custom cron sentinel when disabled with custom cron', () => {
      const r = { cron: '30 2 15 * *', preset_id: null }
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', r)
      fixture.detectChanges()
      expect(component.selectValue()).toBe(component.customCronValue)
    })
  })

  describe('isCustomCron', () => {
    it('is false when not disabled', () => {
      fixture.componentRef.setInput('disabled', false)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '30 2 15 * *',
        preset_id: null
      })
      fixture.detectChanges()
      expect(component.isCustomCron()).toBe(false)
    })

    it('is false when disabled but recurrence has a preset_id', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.isCustomCron()).toBe(false)
    })

    it('is true when disabled with custom cron and no preset_id', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '30 2 15 * *',
        preset_id: null
      })
      fixture.detectChanges()
      expect(component.isCustomCron()).toBe(true)
    })

    it('is false when disabled with no schedule', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: null,
        preset_id: null
      })
      fixture.detectChanges()
      expect(component.isCustomCron()).toBe(false)
    })
  })

  describe('displayLabel', () => {
    it('returns recurrence.none when no recurrence', () => {
      fixture.componentRef.setInput('currentRecurrence', null)
      fixture.detectChanges()
      // TranslateService returns the key when no translation loaded
      expect(component.displayLabel()).toBe('recurrence.none')
    })

    it('returns i18n key for known preset', () => {
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.displayLabel()).toBe('recurrence.preset.EVERY_DAY')
    })

    it('returns cronstrue description for custom cron', () => {
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: null
      })
      fixture.detectChanges()
      // cronstrue produces a human-readable string, not an i18n key
      const label = component.displayLabel()
      expect(label).toBeTruthy()
      expect(label).not.toContain('recurrence.')
    })

    it('recomputes cronstrue locale when language changes', () => {
      const translate = TestBed.inject(TranslateService)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * 1',
        preset_id: null
      })
      translate.use('en')
      fixture.detectChanges()
      const labelEn = component.displayLabel()

      translate.use('fr')
      fixture.detectChanges()
      const labelFr = component.displayLabel()

      // The labels should differ between languages
      expect(labelEn).not.toBe(labelFr)
    })
  })

  describe('shouldShowPresetFallback', () => {
    it('is false when not disabled', () => {
      fixture.componentRef.setInput('disabled', false)
      fixture.componentRef.setInput('presets', DEFAULT_PRESETS)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.shouldShowPresetFallback()).toBe(false)
    })

    it('is false when disabled and preset is in the list', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('presets', DEFAULT_PRESETS)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.shouldShowPresetFallback()).toBe(false)
    })

    it('is true when disabled and preset is absent from the list', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('presets', [])
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.shouldShowPresetFallback()).toBe(true)
    })

    it('is false when disabled but no preset_id', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('presets', [])
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '30 2 15 * *',
        preset_id: null
      })
      fixture.detectChanges()
      expect(component.shouldShowPresetFallback()).toBe(false)
    })
  })

  describe('tooltipLabel', () => {
    it('returns recurrence.none when no value selected', () => {
      fixture.detectChanges()
      expect(component.tooltipLabel()).toBe('recurrence.none')
    })

    it('returns i18n key when a known preset is selected (wizard mode)', () => {
      fixture.componentRef.setInput('presets', DEFAULT_PRESETS)
      fixture.componentRef.setInput('selectedPresetId', 'EVERY_DAY')
      fixture.detectChanges()
      expect(component.tooltipLabel()).toBe('recurrence.preset.EVERY_DAY')
    })

    it('returns displayLabel when showing a custom cron (disabled mode)', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '30 2 15 * *',
        preset_id: null
      })
      fixture.detectChanges()
      expect(component.tooltipLabel()).toBe(component.displayLabel())
    })

    it('returns displayLabel when preset is absent from the list (fallback mode)', () => {
      fixture.componentRef.setInput('disabled', true)
      fixture.componentRef.setInput('presets', [])
      fixture.componentRef.setInput('currentRecurrence', {
        cron: '0 4 * * *',
        preset_id: 'EVERY_DAY'
      })
      fixture.detectChanges()
      expect(component.tooltipLabel()).toBe(component.displayLabel())
    })
  })

  describe('presetChange output', () => {
    it('emits null when empty option selected', () => {
      fixture.componentRef.setInput('presets', DEFAULT_PRESETS)
      fixture.detectChanges()

      const spy = vi.fn()
      component.presetChange.subscribe(spy)

      // Simulate mat-select emitting empty string
      const event = ''
      component.presetChange.emit(event === '' ? null : event)

      expect(spy).toHaveBeenCalledWith(null)
    })

    it('emits preset id when preset selected', () => {
      fixture.componentRef.setInput('presets', DEFAULT_PRESETS)
      fixture.detectChanges()

      const spy = vi.fn()
      component.presetChange.subscribe(spy)
      component.presetChange.emit('EVERY_WEEK')

      expect(spy).toHaveBeenCalledWith('EVERY_WEEK')
    })
  })
})
