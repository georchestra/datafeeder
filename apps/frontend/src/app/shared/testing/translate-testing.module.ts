import { ModuleWithProviders } from '@angular/core'
import {
  TranslateCompiler,
  TranslateLoader,
  TranslateModule,
  TranslateModuleConfig,
  TranslationObject
} from '@ngx-translate/core'
import { Observable, of } from 'rxjs'

type Translations = Record<string, unknown>
type LanguageTranslations = Record<string, Translations>

class StaticTranslateLoader implements TranslateLoader {
  private translations: LanguageTranslations

  constructor(translations: LanguageTranslations) {
    this.translations = translations
  }

  getTranslation(lang: string): Observable<TranslationObject> {
    return of((this.translations[lang] ?? {}) as TranslationObject)
  }
}

/**
 * Drop-in replacement for ngx-translate-testing's TranslateTestingModule,
 * which is incompatible with @ngx-translate/core >=16 (it imports
 * TranslateFakeCompiler/FakeMissingTranslationHandler, both removed, and
 * instantiates TranslateService with a constructor signature that no
 * longer exists). Built on TranslateModule.forRoot() instead. Only supports
 * the single-language builder shape actually used in this codebase's specs.
 */
export class TranslateTestingModule
  implements ModuleWithProviders<TranslateModule>
{
  private translations: LanguageTranslations
  private fallbackLang?: string
  private compiler?: TranslateCompiler

  static withTranslations(
    translations: LanguageTranslations
  ): TranslateTestingModule {
    const instance = new TranslateTestingModule()
    instance.translations = translations
    return instance
  }

  withDefaultLanguage(language: string): TranslateTestingModule {
    this.fallbackLang = language
    return this
  }

  withCompiler(compiler: TranslateCompiler): TranslateTestingModule {
    this.compiler = compiler
    return this
  }

  get ngModule() {
    return TranslateModule
  }

  get providers() {
    const config: TranslateModuleConfig = {
      loader: {
        provide: TranslateLoader,
        useValue: new StaticTranslateLoader(this.translations)
      },
      fallbackLang: this.fallbackLang
    }
    if (this.compiler) {
      config.compiler = { provide: TranslateCompiler, useValue: this.compiler }
    }
    return TranslateModule.forRoot(config).providers
  }
}
