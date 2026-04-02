## Purpose

Handles displaying error messages as persistent toasts in the datafeeder application, informing the user of operation failures while preserving their navigation context.

## Requirements

### Requirement: Persistent error toast on operation failure

The system SHALL display an error toast when any of the following operations fail: metadata save, GeoNetwork/GeoServer (un)publication, GeoNetwork/GeoServer rights editing, recurrence editing, dataset deletion.

#### Scenario: Operation failure triggered by a button

- **WHEN** the user clicks a button that triggers an operation and that operation returns an error
- **THEN** an error toast is displayed with the operation name in the message (e.g. "Metadata save encountered an error")
- **THEN** the triggering button becomes interactive again

#### Scenario: Toast displayed with expected visual elements

- **WHEN** an error toast is displayed
- **THEN** the toast contains a warning triangle icon
- **THEN** the toast contains the error message including the operation name
- **THEN** the toast contains a close button (×)

### Requirement: Toast persistence across navigation

The error toast SHALL remain displayed even if the user navigates to another page, until explicitly closed.

#### Scenario: Navigation after a toast appears

- **WHEN** an error toast is displayed
- **WHEN** the user navigates to another route
- **THEN** the toast remains visible

#### Scenario: Manual toast close

- **WHEN** an error toast is displayed
- **WHEN** the user clicks the toast's close button
- **THEN** the toast disappears

### Requirement: Toast positioned within the application area

The error toast SHALL be positioned inside the application container, independently of any header injected above the application root (e.g. the geOrchestra header).

#### Scenario: Toast visible in the application area with an external header

- **GIVEN** the application is deployed in a context where an external header (geOrchestra) is injected above `<app-root>`
- **WHEN** an error toast is displayed
- **THEN** the toast is visible within the application area, without overlapping the external header

### Requirement: Multiple toast stacking

If multiple errors occur, toasts SHALL stack, with the most recent toast appearing at the bottom of the list.

#### Scenario: Two successive errors

- **WHEN** a first operation fails and a toast is displayed
- **WHEN** a second operation fails before the user closes the first toast
- **THEN** two toasts are visible simultaneously
- **THEN** the toast for the second error is positioned below the first

#### Scenario: Individual close of a toast in a stack

- **WHEN** multiple toasts are displayed
- **WHEN** the user closes one of them
- **THEN** only that toast disappears
- **THEN** the other toasts remain displayed
