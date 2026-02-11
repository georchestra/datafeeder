import { Component, input, output } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirSearch, iconoirXmark } from '@ng-icons/iconoir'

@Component({
  selector: 'app-search-input',
  imports: [FormsModule, NgIconComponent],
  templateUrl: './search-input.component.html',
  providers: [
    provideIcons({
      iconoirSearch,
      iconoirXmark
    })
  ]
})
export class SearchInputComponent {
  placeholder = input('')
  value = input('')

  valueChange = output<string>()
  clear = output<void>()
}
