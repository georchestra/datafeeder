Write a technical plan with the following points:

skills:
- use the skills you find in this project (when needed)
backend:
- the result of the final transformation should be written in the property "integrity_transformation" in integrity_link.py. We need an explicit pydantic model for this json object.
- Refactor the staging backend to clarify the separation between configuration persistence and data preview. The PUT metadata endpoint should now accept the full transformation configuration as a JSON object (including projection, x/y column mappings, and any other transformation parameters) and save it to the database on each modification by the user, allowing incremental persistence of user choices as they configure the dataset (no default config exists, initial state is empty). The GET preview endpoint should remove all transformation config parameters and instead read the saved configuration from the database by default to apply transformations, but add a new `raw` boolean query parameter where `raw=false` (default) returns transformed data with the saved config applied, and `raw=true` returns the original data without any transformations. This `raw` parameter is critical because if the user's configuration choices break the preview (wrong projection, invalid columns, etc.), the frontend can request raw data to always display the original table alongside error messages, helping users debug their configuration. The frontend drives all updates by calling PUT metadata on each modification and requests preview with or without transformations using the `raw` parameter, while the backend's responsibility is to persist configuration state and apply saved transformations when generating previews unless `raw=true` is specified.
data-manipulation:
- Add unit tests for functions in data-manipulation library related to this feature
frontend:
- Component where to implement the feature: data-import-wizard.component
- figma mockups for all screens of the feature are here: https://www.figma.com/design/IwMxmE9G9D9StF2QLlR1uE/ingestion-donn%C3%A9es?node-id=655-22462&t=LSTvLADkYUFxpq2F-0 (use the figma mcp when you implement)
- For the UI use tailwindcss classes (no custom css) and follow the design system in the figma (components, colors, spacing, etc.)
- For UI components use geonetwork-ui components where possible (gn-ui-button, gn-ui-text-input) and otherwise angular material components
- Generate the api models and endpoints with the command `npm run generate-api` after implementing the backend changes, to keep the frontend in sync with the backend API (check frontend README for details on generating the API client)
- Add unit tests for each component and service

Notes:
- At the end of the implementation, remove all comments related to the implementation plan and specific to speckit.
- Git commit your work at each significant step of the implementation, with clear commit messages describing the changes made. This will help maintain a clear history of the development process and make it easier to review changes later on.
- Pause the implementation inside copilot chat after each phase so I can manually review the code changes.