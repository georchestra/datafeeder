import { TestBed } from '@angular/core/testing'
import { ColumnHeaderComponent } from './column-header.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { ColumnConfigOutput } from '../../../core/api/models'

const translations = {
  'import.columnAction.menu.filter': 'Filtrer la colonne',
  'import.columnAction.menu.changeType': 'Changer le type',
  'import.columnAction.menu.remove': 'Retirer la colonne'
}

const baseColumnConfig: ColumnConfigOutput = {
  original_name: 'my_column',
  new_name: null,
  excluded: false,
  cast_type: null,
  filter: null
}

describe('ColumnHeaderComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ColumnHeaderComponent,
        TranslateTestingModule.withTranslations({ fr: translations })
          .withDefaultLanguage('fr')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should render the column name', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const input = compiled.querySelector('input') as HTMLInputElement
    expect(input?.value).toBe('my_column')
  })

  it('should render the new_name when set', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      new_name: 'renamed_column'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const input = compiled.querySelector('input') as HTMLInputElement
    expect(input?.value).toBe('renamed_column')
  })

  it('should render the action button', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const actionBtn = compiled.querySelector('[data-action-button]')
    expect(actionBtn).toBeTruthy()
  })

  it('should NOT show indicator dot when no actions are configured', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeNull()
  })

  it('should show indicator dot when filter is active', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      filter: { operator: 'contains', value: 'test' }
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeTruthy()
  })

  it('should show indicator dot when cast_type is set', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', {
      ...baseColumnConfig,
      cast_type: 'numeric'
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const dot = compiled.querySelector('[data-active-indicator]')
    expect(dot).toBeTruthy()
  })

  it('should open the action menu when action button is clicked', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-column-action-menu')).toBeNull()

    const actionBtn = compiled.querySelector('[data-action-button]') as HTMLElement
    actionBtn.click()
    fixture.detectChanges()

    expect(compiled.querySelector('app-column-action-menu')).toBeTruthy()
  })

  it('should emit actionMenuOpened when an action is selected from the open menu', () => {
    const fixture = TestBed.createComponent(ColumnHeaderComponent)
    fixture.componentRef.setInput('columnConfig', baseColumnConfig)
    fixture.detectChanges()

    const emitted: string[] = []
    fixture.componentInstance.actionMenuOpened.subscribe((a) => emitted.push(a))

    const compiled = fixture.nativeElement as HTMLElement
    // Open the menu
    const actionBtn = compiled.querySelector('[data-action-button]') as HTMLElement
    actionBtn.click()
    fixture.detectChanges()

    // Click an action item ("filter") in the opened menu
    const filterBtn = compiled.querySelector('[data-action="filter"]') as HTMLElement
    filterBtn.click()
    fixture.detectChanges()

    expect(emitted.length).toBeGreaterThan(0)
    expect(emitted[0]).toBe('filter')
  })
})
