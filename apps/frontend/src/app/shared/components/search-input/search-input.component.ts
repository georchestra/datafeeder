import { Component, input, model } from '@angular/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirSearch, iconoirXmark } from '@ng-icons/iconoir'

@Component({
  selector: 'app-search-input',
  imports: [NgIconComponent],
  templateUrl: './search-input.component.html',
  providers: [
    provideIcons({
      iconoirSearch,
      iconoirXmark
    })
  ]
})
export class SearchInputComponent {
  fullWidth = input(false)
  placeholder = input('')
  value = model('')
}
