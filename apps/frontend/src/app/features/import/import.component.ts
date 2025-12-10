import { Component } from '@angular/core'
import { DataImportWizardComponent } from '../../shared/components/data-import-wizard/data-import-wizard.component'

@Component({
  selector: 'app-import',
  imports: [DataImportWizardComponent],
  templateUrl: './import.component.html'
})
export class ImportComponent {}
