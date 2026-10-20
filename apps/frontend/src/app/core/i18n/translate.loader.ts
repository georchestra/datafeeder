import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { TranslateLoader, TranslationObject } from '@ngx-translate/core'
import { dropEmptyTranslations, getCustomTranslations } from 'geonetwork-ui'
import { forkJoin, map, Observable } from 'rxjs'

@Injectable()
export class DatafeederTranslateLoader implements TranslateLoader {
  private http = inject(HttpClient)

  getTranslation(lang: string): Observable<TranslationObject> {
    const baseLang = lang.substring(0, 2)
    return forkJoin([
      this.http.get(`./assets/i18n/gn-ui/${baseLang}.json`),
      this.http.get(`./assets/i18n/${baseLang}.json`)
    ]).pipe(
      map(([gnUi, datafeeder]) => ({
        ...dropEmptyTranslations(gnUi),
        ...dropEmptyTranslations(datafeeder),
        ...getCustomTranslations(baseLang)
      }))
    )
  }
}
