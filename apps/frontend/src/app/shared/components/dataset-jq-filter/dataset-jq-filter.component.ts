import { ChangeDetectionStrategy, Component, input } from '@angular/core'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { TranslatePipe } from '@ngx-translate/core'
import type { StagingMetadataResponse } from '../../../core/api/models'

@Component({
  selector: 'app-dataset-jq-filter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatFormFieldModule, MatInputModule, TranslatePipe],
  templateUrl: './dataset-jq-filter.component.html'
})
export class DatasetJqFilterComponent {
  metadata = input<StagingMetadataResponse | null>(null)

  // Not yet user-configurable; the seam a future editable jq filter plugs into.
  readonly defaultFilter = '.'
}
