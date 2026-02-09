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
        'gray-2': '#4C4C4C',
        'secondary-hover': '#A1DBDE',
        'secondary-active': 'rgba(161, 219, 222, 0.4)',
      },
    },
  },
  safelist: [
    'max-h-14', 'w-48'
  ],
  plugins: [],
}
