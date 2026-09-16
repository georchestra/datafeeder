import { TestBed } from '@angular/core/testing'
import { MultiSelectDropdownComponent } from './multi-select-dropdown.component'
import { TranslateTestingModule } from '../../testing/translate-testing.module'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

const translations = {
  'filters.access': 'Access',
  'integrityLinks.visibility.open': 'Open',
  'integrityLinks.visibility.restricted': 'Restricted',
  // Deliberately registered so the raw-label test would fail if translateChoices
  // were ignored and the pipe applied anyway (a missing key would render as-is,
  // masking the bug).
  Camptocamp: 'Should not be translated'
}

const choices = [
  { id: 'open', label: 'integrityLinks.visibility.open' },
  { id: 'restricted', label: 'integrityLinks.visibility.restricted' }
]

// CDK Overlay renders its content into a `.cdk-overlay-container` appended to
// document.body, not inside fixture.nativeElement — queries below use
// `document` rather than the fixture root for anything inside the panel.
async function openPanel(
  fixture: ReturnType<typeof TestBed.createComponent>
): Promise<void> {
  const trigger = fixture.nativeElement.querySelector('button') as HTMLElement
  trigger.click()
  fixture.detectChanges()
  await fixture.whenStable()
  fixture.detectChanges()
}

describe('MultiSelectDropdownComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MultiSelectDropdownComponent,
        TranslateTestingModule.withTranslations({ en: translations })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should not render choices until the trigger is clicked', () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.detectChanges()

    expect(document.querySelectorAll('input[type=checkbox]').length).toBe(0)
  })

  it('should render one checkbox per choice after opening', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.detectChanges()

    await openPanel(fixture)

    expect(document.querySelectorAll('input[type=checkbox]').length).toBe(2)
  })

  it('should add an id to selected when its checkbox is checked', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.detectChanges()

    await openPanel(fixture)

    const checkbox = document.querySelectorAll(
      'input[type=checkbox]'
    )[0] as HTMLInputElement
    checkbox.click()
    fixture.detectChanges()

    expect(fixture.componentInstance.selected()).toEqual(['open'])
  })

  it('should remove an id from selected when its checkbox is unchecked', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.componentRef.setInput('selected', ['open', 'restricted'])
    fixture.detectChanges()

    await openPanel(fixture)

    const checkbox = document.querySelectorAll(
      'input[type=checkbox]'
    )[0] as HTMLInputElement
    checkbox.click()
    fixture.detectChanges()

    expect(fixture.componentInstance.selected()).toEqual(['restricted'])
  })

  it('should show an indicator dot when a choice is selected', () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.componentRef.setInput('selected', ['open'])
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-indicator-dot]')).toBeTruthy()
  })

  it('should not show an indicator dot when nothing is selected', () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('[data-indicator-dot]')).toBeNull()
  })

  it('should keep the inner checkboxes out of the tab order', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', choices)
    fixture.detectChanges()

    await openPanel(fixture)

    const checkbox = document.querySelector(
      'input[type=checkbox]'
    ) as HTMLInputElement
    expect(checkbox.getAttribute('tabindex')).toBe('-1')
  })

  it('should render the raw choice label when translateChoices is false', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', [
      { id: 'c2c', label: 'Camptocamp' }
    ])
    fixture.componentRef.setInput('translateChoices', false)
    fixture.detectChanges()

    await openPanel(fixture)

    expect(document.querySelector('label span')?.textContent?.trim()).toBe(
      'Camptocamp'
    )
  })

  it('should resolve keyboard opening when there are no choices', async () => {
    const fixture = TestBed.createComponent(MultiSelectDropdownComponent)
    fixture.componentRef.setInput('label', 'filters.access')
    fixture.componentRef.setInput('choices', [])
    fixture.detectChanges()

    const opened = fixture.componentInstance.handleTriggerKeydown(
      new KeyboardEvent('keydown', { code: 'Enter' })
    )
    fixture.detectChanges()
    await fixture.whenStable()

    await expect(opened).resolves.toBeUndefined()
    expect(fixture.componentInstance.overlayOpen).toBe(true)
  })
})
