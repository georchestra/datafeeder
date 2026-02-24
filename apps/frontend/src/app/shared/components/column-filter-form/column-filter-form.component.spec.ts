import { TestBed } from '@angular/core/testing'
import { ColumnFilterFormComponent } from './column-filter-form.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { ColumnFilter } from '../../../core/api/models/column-filter'

const translations = {
  'import.columnFilter.operator.exactly': 'Exactement',
  'import.columnFilter.operator.contains': 'Contient',
  'import.columnFilter.operator.starts_with': 'Commence par',
  'import.columnFilter.valuePlaceholder': 'Valeur...',
  'import.columnFilter.validate': 'Valider',
  'import.columnFilter.delete': 'Supprimer'
}

describe('ColumnFilterFormComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ColumnFilterFormComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render all three operator inputs in editing state (no active filter)', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-contains-input]')).toBeTruthy()
    expect(compiled.querySelector('[data-exactly-input]')).toBeTruthy()
    expect(compiled.querySelector('[data-starts-with-input]')).toBeTruthy()
  })

  it('should render one dedicated input per operator', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-contains-input]')).toBeTruthy()
    expect(compiled.querySelector('[data-exactly-input]')).toBeTruthy()
    expect(compiled.querySelector('[data-starts-with-input]')).toBeTruthy()
  })

  it('should emit filterValidated with operator and value on input submit', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.detectChanges()

    const emitted: ColumnFilter[] = []
    fixture.componentInstance.filterValidated.subscribe((f) => emitted.push(f))

    const compiled = fixture.nativeElement as HTMLElement
    const input = compiled.querySelector(
      '[data-exactly-input]'
    ) as HTMLInputElement
    input.value = 'test value'
    input.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    const submitBtn = compiled.querySelector(
      '[data-submit-exactly]'
    ) as HTMLElement
    submitBtn.click()
    fixture.detectChanges()

    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toEqual({ operator: 'exactly', value: 'test value' })
  })

  it('should NOT emit filterValidated when value is empty', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.detectChanges()

    const emitted: ColumnFilter[] = []
    fixture.componentInstance.filterValidated.subscribe((f) => emitted.push(f))

    const compiled = fixture.nativeElement as HTMLElement
    // Submit buttons are only rendered when their input has a non-empty value
    expect(compiled.querySelector('[data-submit-contains]')).toBeNull()
    expect(compiled.querySelector('[data-submit-exactly]')).toBeNull()
    expect(compiled.querySelector('[data-submit-starts-with]')).toBeNull()
    expect(emitted).toHaveLength(0)
  })

  it('should show read-only active filter display when activeFilter is set', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.componentRef.setInput('activeFilter', {
      operator: 'contains',
      value: 'hello'
    } as ColumnFilter)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const activeFilter = compiled.querySelector('[data-active-filter]')
    expect(activeFilter).toBeTruthy()
    expect(activeFilter?.textContent).toContain('Contient')
    expect(activeFilter?.textContent).toContain('hello')
    // Should NOT show editing controls
    expect(compiled.querySelector('[data-filter-value-input]')).toBeNull()
    expect(compiled.querySelector('[data-validate-button]')).toBeNull()
  })

  it('should show delete button on active filter', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.componentRef.setInput('activeFilter', {
      operator: 'contains',
      value: 'hello'
    } as ColumnFilter)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-delete-button]')).toBeTruthy()
  })

  it('should emit filterDeleted when delete button is clicked', () => {
    const fixture = TestBed.createComponent(ColumnFilterFormComponent)
    fixture.componentRef.setInput('activeFilter', {
      operator: 'contains',
      value: 'hello'
    } as ColumnFilter)
    fixture.detectChanges()

    let deleted = false
    fixture.componentInstance.filterDeleted.subscribe(() => {
      deleted = true
    })

    const compiled = fixture.nativeElement as HTMLElement
    const deleteBtn = compiled.querySelector(
      '[data-delete-button]'
    ) as HTMLElement
    deleteBtn.click()
    fixture.detectChanges()

    expect(deleted).toBe(true)
  })
})
