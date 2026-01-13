/* eslint-disable no-undef */
const baseConfig = require('./node_modules/geonetwork-ui/tailwind.base.config')
const { join } = require('path')

/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [baseConfig],
  content: [
    './node_modules/geonetwork-ui/**/*.mjs',
    join(__dirname, 'src/**/!(*.stories|*.spec).{ts,html}'),
  ],
  theme: {
    extend: {
      colors: {
        beige: '#F7F5F0',
      },
    },
  },
  safelist: [
    'max-h-14', 'w-48'
  ],
  plugins: [],
}
