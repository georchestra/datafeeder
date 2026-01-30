import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { provideRouter } from '@angular/router'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { ApiConfiguration } from '../../core/api/api-configuration'
import { ImportComponent } from './import.component'

describe('ImportComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ImportComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.title': 'Add a dataset'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        }
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should display tab labels', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Add a dataset')
  })

  it('should render data import wizard', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-data-import-wizard')).toBeTruthy()
  })
})
