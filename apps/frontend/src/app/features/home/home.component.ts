import { Component } from '@angular/core'
import { MatButtonModule } from '@angular/material/button'
import { MatCheckboxModule } from '@angular/material/checkbox'

@Component({
  selector: 'app-home',
  imports: [MatButtonModule, MatCheckboxModule],
  template: `
    <div class="space-y-4 py-8">
      <h1 class="text-2xl font-bold">Home page</h1>

      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
        veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat.
      </p>

      <div class="flex items-center gap-4">
        <button mat-raised-button color="primary">Click me</button>
        <mat-checkbox>Check this</mat-checkbox>
      </div>
    </div>
  `
})
export class HomeComponent {}
