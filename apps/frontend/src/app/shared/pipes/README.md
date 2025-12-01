# Shared Pipes

This folder contains custom Angular pipes for data transformation in templates.

## Purpose

Pipes transform data for display purposes without modifying the underlying data:
- Format dates, numbers, and currencies
- Filter and sort collections
- Transform strings (capitalization, truncation, etc.)
- Convert data structures for display

## Examples

Common shared pipes include:
- Custom date formatters
- Number formatters
- Text truncation
- Safe HTML/URL sanitization
- Pluralization helpers
- Enum to display name converters

## Guidelines

- Keep pipes pure for better performance
- Handle null/undefined values gracefully
- Document expected input/output formats
