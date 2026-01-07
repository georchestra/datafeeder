import { Component, input, computed } from '@angular/core'
import { MatTableModule } from '@angular/material/table'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'

@Component({
  selector: 'app-dataset-preview-table',
  imports: [MatTableModule],
  templateUrl: './dataset-preview-table.component.html',
  styleUrls: ['./dataset-preview-table.component.scss']
})
export class DatasetPreviewTableComponent {
  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)

  displayedColumns = computed(() => {
    const meta = this.metadata()
    return meta?.columns.map((col) => col.name) || []
  })

  dataSource = computed(() => {
    const data = this.preview()?.data || []
    return data
  })
}
