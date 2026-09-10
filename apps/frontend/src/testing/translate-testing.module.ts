import { EnvironmentProviders, NgModule, Provider } from '@angular/core'
import {
  TranslateCompiler,
  TranslateLoader,
  TranslateModule,
  TranslationObject
} from '@ngx-translate/core'
import { Observable, of } from 'rxjs'

export type Translations = Record<string, TranslationObject>

class TestTranslateLoader extends TranslateLoader {
  private readonly translations: Translations

  constructor(translations: Translations) {
    super()
    this.translations = translations
  }

  getTranslation(language: string): Observable<TranslationObject> {
    return of(this.translations[language] ?? {})
  }
}

/**
 * Replaces the `ngx-translate-testing` package, unmaintained since 2023: it
 * instantiated TranslateService by hand with positional arguments, including
 * FakeMissingTranslationHandler and TranslateFakeCompiler, both removed in
 * @ngx-translate/core 17. Going through TranslateModule.forRoot() instead lets
 * Angular build the service, so internal changes no longer break the tests.
 */
@NgModule()
export class TranslateTestingModule {
  private translations: Translations = {}
  private defaultLanguage?: string
  private compiler?: TranslateCompiler

  static withTranslations(translations: Translations): TranslateTestingModule {
    return new TranslateTestingModule().withTranslations(translations)
  }

  withTranslations(translations: Translations): this {
    Object.entries(translations).forEach(([language, values]) => {
      this.translations[language] = {
        ...this.translations[language],
        ...values
      }
    })
    return this
  }

  withDefaultLanguage(language: string): this {
    this.defaultLanguage = language
    return this
  }

  withCompiler(compiler: TranslateCompiler): this {
    this.compiler = compiler
    return this
  }

  // Angular reads ngModule/providers off whatever `imports` receives, so the
  // builder itself can stand in for a ModuleWithProviders.
  get ngModule(): typeof TranslateTestingModule {
    return TranslateTestingModule
  }

  get providers(): (Provider | EnvironmentProviders)[] {
    const language = this.defaultLanguage ?? Object.keys(this.translations)[0]
    return (
      TranslateModule.forRoot({
        lang: language,
        fallbackLang: language,
        loader: {
          provide: TranslateLoader,
          useValue: new TestTranslateLoader(this.translations)
        },
        ...(this.compiler
          ? {
              compiler: { provide: TranslateCompiler, useValue: this.compiler }
            }
          : {})
      }).providers ?? []
    )
  }
}
