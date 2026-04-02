## ADDED Requirements

### Requirement: Confirmation modal for destructive actions

The system SHALL display a confirmation dialog modal before executing a destructive action (e.g. deleting a dataset). The modal uses `ConfirmationDialogComponent` from `geonetwork-ui`, opened via `MatDialog`.

#### Scenario: Modal display

- **WHEN** the user triggers a destructive action (e.g. clicks the delete button)
- **THEN** a confirmation modal appears over the content, with a semi-transparent backdrop blocking interaction with the rest of the interface

#### Scenario: Action confirmed

- **WHEN** the user clicks the confirmation button (e.g. "Delete")
- **THEN** the modal closes and the destructive action is executed

#### Scenario: Action cancelled

- **WHEN** the user clicks the cancel button (e.g. "Cancel")
- **THEN** the modal closes without executing the destructive action

#### Scenario: Closed via Escape key

- **WHEN** the user presses the Escape key while the modal is open
- **THEN** the modal closes without executing the destructive action

#### Scenario: Closed by clicking the backdrop

- **WHEN** the user clicks the semi-transparent backdrop outside the modal
- **THEN** the modal closes without executing the destructive action

### Requirement: Configurable modal content

The modal SHALL display a title, message, and button labels provided by the caller. It SHALL NOT contain hard-coded text.

#### Scenario: Custom title and message

- **WHEN** the modal is opened with a specific title and message
- **THEN** those texts are displayed correctly in the modal

#### Scenario: Default button labels

- **WHEN** no custom labels are provided
- **THEN** default labels are used ("Confirm" and "Cancel" or equivalent in the active language)

### Requirement: Danger visual variant

The modal SHALL support a `danger` variant that highlights the destructive nature of the action via the confirmation button style (red).

#### Scenario: Confirmation button in red for danger variant

- **WHEN** the modal is opened with the `danger` variant
- **THEN** the confirmation button is displayed in red (destructive styling)

### Requirement: Keyboard accessibility

The modal SHALL trap focus inside the dialog while open, and restore it to the triggering element on close.

#### Scenario: Focus trapped in modal

- **WHEN** the modal is open
- **THEN** keyboard navigation (Tab) is confined to the interactive elements within the modal

#### Scenario: Focus restoration

- **WHEN** the modal closes (confirmation or cancellation)
- **THEN** focus returns to the element that triggered the opening

### Requirement: Integration in the dataset deletion flow

The `integrity-link-list` component SHALL use `ConfirmationDialogComponent` from `geonetwork-ui` instead of `window.confirm()` when deleting a dataset.

#### Scenario: Deletion confirmed via modal

- **WHEN** the user confirms deletion via the modal
- **THEN** the deletion API call is made and the row disappears from the list

#### Scenario: Deletion cancelled via modal

- **WHEN** the user cancels deletion via the modal
- **THEN** no API call is made and the dataset remains in the list
