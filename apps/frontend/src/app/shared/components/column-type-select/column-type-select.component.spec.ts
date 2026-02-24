import { TestBed } from '@angular/core/testing'
import { ColumnTypeSelectComponent } from './column-type-select.component'
import type { CastType } from './column-type-select.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

const translations = {
  'import.columnAction.typeMenu.boolean': 'Booléen',
  'import.columnAction.typeMenu.numeric': 'Numérique',
  'import.columnAction.typeMenu.text': 'Texte',
  'import.columnAction.typeMenu.date': 'Date'
}

describe('ColumnTypeSelectComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ColumnTypeSelectComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.detectChanges()
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render a data-type-submenu wrapper div', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.detectChanges()
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[data-type-submenu]')
    ).toBeTruthy()
  })

  it('should render 3 buttons (boolean, numeric, text) when originalType is not date', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelectorAll('[data-type]').length).toBe(3)
  })

  it('should render all 4 buttons including date when originalType is date', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.componentRef.setInput('originalType', 'date')
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelectorAll('[data-type]').length).toBe(4)
  })

  it('should set aria-selected="true" on the castType option', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.componentRef.setInput('castType', 'numeric')
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(
      compiled
        .querySelector('[data-type="numeric"]')
        ?.getAttribute('aria-selected')
    ).toBe('true')
    expect(
      compiled
        .querySelector('[data-type="boolean"]')
        ?.getAttribute('aria-selected')
    ).toBe('false')
    expect(
      compiled
        .querySelector('[data-type="text"]')
        ?.getAttribute('aria-selected')
    ).toBe('false')
  })

  it('should emit the clicked type when it is not the active type', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.detectChanges()

    const emitted: Array<CastType | null> = []
    fixture.componentInstance.typeSelect.subscribe((t) => emitted.push(t))

    const compiled = fixture.nativeElement as HTMLElement
    const numericBtn = compiled.querySelector(
      '[data-type="numeric"]'
    ) as HTMLElement
    numericBtn.click()
    fixture.detectChanges()

    expect(emitted).toEqual(['numeric'])
  })

  it('should emit null when the currently active castType is re-clicked', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.componentRef.setInput('castType', 'numeric')
    fixture.detectChanges()

    const emitted: Array<CastType | null> = []
    fixture.componentInstance.typeSelect.subscribe((t) => emitted.push(t))

    const compiled = fixture.nativeElement as HTMLElement
    const numericBtn = compiled.querySelector(
      '[data-type="numeric"]'
    ) as HTMLElement
    numericBtn.click()
    fixture.detectChanges()

    expect(emitted).toEqual([null])
  })

  it('should display translated label for each type', () => {
    const fixture = TestBed.createComponent(ColumnTypeSelectComponent)
    fixture.componentRef.setInput('originalType', 'date')
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Booléen')
    expect(compiled.textContent).toContain('Numérique')
    expect(compiled.textContent).toContain('Texte')
    expect(compiled.textContent).toContain('Date')
  })
})
