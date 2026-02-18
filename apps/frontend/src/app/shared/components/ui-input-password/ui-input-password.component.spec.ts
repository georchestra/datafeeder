import { TestBed } from '@angular/core/testing'
import { UiInputPasswordComponent } from './ui-input-password.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

describe('UiInputPasswordComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        UiInputPasswordComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'input.password.hide': 'Hide password',
            'input.password.show': 'Show password'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(UiInputPasswordComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should initially hide password', () => {
    const fixture = TestBed.createComponent(UiInputPasswordComponent)
    const component = fixture.componentInstance
    expect(component.showPassword()).toBe(false)
  })

  it('should toggle password visibility', () => {
    const fixture = TestBed.createComponent(UiInputPasswordComponent)
    const component = fixture.componentInstance

    expect(component.showPassword()).toBe(false)

    component.togglePasswordVisibility()
    expect(component.showPassword()).toBe(true)

    component.togglePasswordVisibility()
    expect(component.showPassword()).toBe(false)
  })

  it('should emit valueChange when input changes', () => {
    const fixture = TestBed.createComponent(UiInputPasswordComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    let emittedValue: string | undefined

    component.valueChange.subscribe((value) => {
      emittedValue = value
    })

    const input = fixture.nativeElement.querySelector('input')
    input.value = 'test-password'
    input.dispatchEvent(new Event('input'))

    expect(emittedValue).toBe('test-password')
  })

  it('should change input type when toggling visibility', () => {
    const fixture = TestBed.createComponent(UiInputPasswordComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    const input = fixture.nativeElement.querySelector('input')
    expect(input.type).toBe('password')

    component.togglePasswordVisibility()
    fixture.detectChanges()

    expect(input.type).toBe('text')
  })
})
