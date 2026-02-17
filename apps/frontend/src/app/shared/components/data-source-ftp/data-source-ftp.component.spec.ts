import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { DataSourceFtpComponent } from './data-source-ftp.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

describe('DataSourceFtpComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataSourceFtpComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.ftp.host': 'Host',
            'import.dataSource.ftp.port': 'Port',
            'import.dataSource.ftp.username': 'Username',
            'import.dataSource.ftp.password': 'Password',
            'import.dataSource.ftp.path': 'Path'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataSourceFtpComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should emit ftpDataChanged when form values change', () => {
    const fixture = TestBed.createComponent(DataSourceFtpComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.ftpDataChanged.subscribe((value) => {
      emittedValue = value
    })

    component.form.patchValue({
      host: 'ftp.example.com',
      port: 2121,
      username: 'user',
      password: 'pass',
      path: '/files/data.csv'
    })

    expect(emittedValue).toEqual({
      host: 'ftp.example.com',
      port: 2121,
      username: 'user',
      password: 'pass',
      path: '/files/data.csv'
    })
  })
})
