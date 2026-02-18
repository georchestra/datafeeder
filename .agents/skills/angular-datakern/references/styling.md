# Styling with Tailwind CSS

## Tailwind Configuration

Tailwind CSS 3 is configured for the project. Use utility classes for all styling.

## Styling Guidelines

### Use Utility Classes

Prefer Tailwind utility classes over custom CSS:

```html
<!-- Good -->
<div class="flex items-center gap-4 p-4 bg-white rounded-lg shadow-md">
  <span class="text-lg font-semibold text-gray-900">Title</span>
</div>

<!-- Avoid custom CSS when utilities exist -->
<div class="custom-card">
  <span class="custom-title">Title</span>
</div>
```

### Component-Specific Styles

When custom styles are needed, use component-scoped CSS files:

```css
/* status-badge.component.css */
.badge-success {
  @apply bg-green-100 text-green-800;
}

.badge-error {
  @apply bg-red-100 text-red-800;
}
```

### Common Patterns

**Flexbox Layouts**:

```html
<div class="flex items-center justify-between gap-4">
  <div>Left content</div>
  <div>Right content</div>
</div>
```

**Grid Layouts**:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div>Card 1</div>
  <div>Card 2</div>
  <div>Card 3</div>
</div>
```

**Responsive Design**:

```html
<div class="text-sm md:text-base lg:text-lg">Responsive text size</div>
```

**Spacing**:

- Use consistent spacing: `gap-2`, `gap-4`, `gap-6`, `gap-8`
- Padding: `p-2`, `p-4`, `p-6`, `p-8`
- Margin: `m-2`, `m-4`, `m-6`, `m-8`

### Colors

Use Tailwind's color palette with semantic naming:

- Primary: `bg-blue-600`, `text-blue-600`
- Success: `bg-green-600`, `text-green-600`
- Warning: `bg-yellow-600`, `text-yellow-600`
- Error: `bg-red-600`, `text-red-600`
- Neutral: `bg-gray-100`, `text-gray-700`

### Typography

- Headings: `text-xl`, `text-2xl`, `text-3xl` with `font-semibold` or `font-bold`
- Body: `text-base`, `text-sm`
- Small: `text-xs`

## Angular Material Integration

Angular Material components are available (@angular/material). Use Material components for complex UI patterns:

- Tabs: `MatTabsModule`
- Button toggles: `MatButtonToggleModule`
- Dialogs: `MatDialogModule`
- Forms: `MatFormFieldModule`

Combine Material components with Tailwind utilities for styling.

## geonetwork-ui Components

Use geonetwork-ui components for geospatial-specific UI:

- `ButtonComponent`
- `SpinningLoaderComponent`
- `FeatureEditorModule`

These components follow the same styling patterns and integrate with Tailwind.
