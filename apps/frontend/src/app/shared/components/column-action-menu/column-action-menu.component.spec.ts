import { TestBed } from '@angular/core/testing'
import { ColumnActionMenuComponent } from './column-action-menu.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { ColumnConfigOutput } from '../../../core/api/models'

const translations = {
  'import.columnAction.menu.filter': 'Filtrer la colonne',
  'import.columnAction.menu.changeType': 'Changer le type',
  'import.columnAction.menu.remove': 'Retirer la colonne'
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

  it('should emit "filter" when filter action is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const filterBtn = compiled.querySelectorAll('[data-action]')[0] as HTMLElement
    filterBtn.click()
    expect(emitted).toContain('filter')
  })

  it('should emit "changeType" when change type action is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const typeBtn = compiled.querySelectorAll('[data-action]')[1] as HTMLElement
    typeBtn.click()
    expect(emitted).toContain('changeType')
  })

  it('should emit "remove" when remove action is clicked', () => {
    const fixture = TestBed.createComponent(ColumnActionMenuComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionSelected.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    const removeBtn = compiled.querySelectorAll('[data-action]')[2] as HTMLElement
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
})
