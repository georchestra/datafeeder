import { TestBed } from '@angular/core/testing'
import { ColumnActionMenuComponent } from './column-action-menu.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { ColumnConfigOutput } from '../../../core/api/models'

const translations = {
  'import.columnAction.menu.filter': 'Filtrer la colonne',
  'import.columnAction.menu.changeType': 'Changer le type',
  'import.columnAction.menu.remove': 'Retirer la colonne',
  'import.columnAction.typeMenu.boolean': 'Booléen',
  'import.columnAction.typeMenu.numeric': 'Numérique',
  'import.columnAction.typeMenu.text': 'Texte',
  'import.columnAction.typeMenu.date': 'Date',
  'import.columnFilter.operator.exactly': 'Exactement',
  'import.columnFilter.operator.contains': 'Contient',
  'import.columnFilter.operator.starts_with': 'Commence par',
  'import.columnFilter.valuePlaceholder': 'Valeur...',
  'import.columnFilter.validate': 'Valider',
  'import.columnFilter.delete': 'Supprimer'
}

const baseColumnConfig: ColumnConfigOutput = {
  original_name: 'col1',
  new_name: null,
  excluded: false,
  cast_type: null,
  filter: null
}

describe('ColumnActionMenuComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ColumnActionMenuComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render all 3 action labels', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Filtrer la colonne')
    expect(compiled.textContent).toContain('Changer le type')
    expect(compiled.textContent).toContain('Retirer la colonne')
  })

  it('should toggle the filter panel when "Filter" action is clicked (does not emit actionSelected)', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const filterBtn = compiled.querySelectorAll(
      '[data-action]'
    )[0] as HTMLElement
    filterBtn.click()
    fixture.detectChanges()

    // Should NOT emit action — instead opens filter panel
    expect(emitted).not.toContain('filter')
    expect(compiled.querySelector('[data-filter-panel]')).toBeTruthy()
  })

  it('should toggle the type submenu when "Change type" is clicked (does not emit actionSelected)', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    // Should NOT emit action — instead opens submenu
    expect(emitted).not.toContain('changeType')
    expect(compiled.querySelector('[data-type-submenu]')).toBeTruthy()
  })

  it('should emit "remove" when remove action is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const removeBtn = compiled.querySelectorAll(
      '[data-action]'
    )[2] as HTMLElement
    removeBtn.click()
    expect(emitted).toContain('remove')
  })

  it('should NOT show indicator dots when no actions are configured', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dots = compiled.querySelectorAll('[data-indicator-dot]')
    expect(dots.length).toBe(0)
  })

  it('should show filter indicator dot when filter is active', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      filter: { operator: 'contains', value: 'test' }
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const filterDot = compiled.querySelector('[data-indicator-dot="filter"]')
    expect(filterDot).toBeTruthy()
  })

  it('should show cast_type indicator dot when cast type is set', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      cast_type: 'numeric'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const typeDot = compiled.querySelector('[data-indicator-dot="changeType"]')
    expect(typeDot).toBeTruthy()
  })

  // --- T031: Type selection submenu ---

  it('should show type submenu with 4 options when "Change type" is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    // Initially hidden
    expect(compiled.querySelector('[data-type-submenu]')).toBeNull()

    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    const submenu = compiled.querySelector('[data-type-submenu]')
    expect(submenu).toBeTruthy()
    expect(compiled.querySelectorAll('[data-type]').length).toBe(4)
  })

  it('should show all 4 type options: boolean, numeric, text, date', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    const typeOptions = Array.from(
      compiled.querySelectorAll('[data-type]')
    ).map((el) => el.getAttribute('data-type'))
    expect(typeOptions).toContain('boolean')
    expect(typeOptions).toContain('numeric')
    expect(typeOptions).toContain('text')
    expect(typeOptions).toContain('date')
  })

  it('should emit typeSelected with type name when a type is selected', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.typeSelected.subscribe((t) => emitted.push(t))

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    const numericBtn = compiled.querySelector(
      '[data-type="numeric"]'
    ) as HTMLElement
    numericBtn.click()
    fixture.detectChanges()

    expect(emitted).toEqual(['numeric'])
  })

  it('should emit typeSelected with null when currently active type is re-selected', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      cast_type: 'numeric'
    })
    fixture.detectChanges()

    const emitted: Array<string | null> = []
    fixture.componentInstance.typeSelected.subscribe((t) => emitted.push(t))

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    // Click the currently active type (numeric) to deselect it
    const numericBtn = compiled.querySelector(
      '[data-type="numeric"]'
    ) as HTMLElement
    numericBtn.click()
    fixture.detectChanges()

    expect(emitted).toEqual([null])
  })

  it('should mark the current cast_type option as active', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      cast_type: 'text'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelector(
      '[data-action="changeType"]'
    ) as HTMLElement
    typeBtn.click()
    fixture.detectChanges()

    const textOption = compiled.querySelector('[data-type="text"]')
    expect(textOption?.getAttribute('aria-selected')).toBe('true')
  })

  // --- T035: Filter integration in action menu ---

  it('should expand filter panel when "Filter" action is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-filter-panel]')).toBeNull()

    const filterBtn = compiled.querySelector(
      '[data-action="filter"]'
    ) as HTMLElement
    filterBtn.click()
    fixture.detectChanges()

    expect(compiled.querySelector('[data-filter-panel]')).toBeTruthy()
  })

  it('should show filter indicator dot when filter is active', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      filter: { operator: 'contains' as const, value: 'hello' }
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-indicator-dot="filter"]')).toBeTruthy()
  })

  it('should emit filterValidated when filter form emits a validated filter', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: Array<{ operator: string; value: string }> = []
    fixture.componentInstance.filterValidated.subscribe((f) => emitted.push(f))

    // Expand filter panel
    const compiled = fixture.nativeElement as HTMLElement
    const filterBtn = compiled.querySelector(
      '[data-action="filter"]'
    ) as HTMLElement
    filterBtn.click()
    fixture.detectChanges()

    // Fill in filter form
    const input = compiled.querySelector(
      '[data-filter-value-input]'
    ) as HTMLInputElement
    input.value = 'test'
    input.dispatchEvent(new Event('input'))
    fixture.detectChanges()

    const validateBtn = compiled.querySelector(
      '[data-validate-button]'
    ) as HTMLElement
    validateBtn.click()
    fixture.detectChanges()

    expect(emitted).toHaveLength(1)
    expect(emitted[0].value).toBe('test')
  })

  it('should emit filterDeleted when active filter delete button is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      filter: { operator: 'contains' as const, value: 'hello' }
    })
    fixture.detectChanges()

    let deleted = false
    fixture.componentInstance.filterDeleted.subscribe(() => {
      deleted = true
    })

    const compiled = fixture.nativeElement as HTMLElement

    // Show the filter panel
    const filterBtn = compiled.querySelector(
      '[data-action="filter"]'
    ) as HTMLElement
    filterBtn.click()
    fixture.detectChanges()

    const deleteBtn = compiled.querySelector(
      '[data-delete-button]'
    ) as HTMLElement
    deleteBtn.click()
    fixture.detectChanges()

    expect(deleted).toBe(true)
  })
})
