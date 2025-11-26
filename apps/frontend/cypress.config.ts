import { defineConfig } from "cypress";
import installLogsPrinter from 'cypress-terminal-report/src/installLogsPrinter';

export default defineConfig({
  e2e: {
    setupNodeEvents(on /*, config*/) {
      installLogsPrinter(on);
    },
  },
});
  