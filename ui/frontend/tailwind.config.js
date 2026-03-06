/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  important: true,
  theme: {
    extend: {
      colors: {
        'cg-blue': '#0070AD',
        'cg-vibrant': '#12ABDB',
        'cg-navy': '#0F172A',
        'cg-dark': '#1E293B',
        'cg-gray': {
          50: '#F8F9FA',
          100: '#E9ECEF',
          200: '#DEE2E6',
          500: '#6C757D',
          900: '#212529',
        },
        'cg-success': '#28A745',
        'cg-error': '#DC3545',
        'cg-warn': '#FFC107',
      },
    },
  },
  plugins: [],
};
