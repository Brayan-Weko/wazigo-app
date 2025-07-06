/** @type {import('tailwindcss').Config} */ 
module.exports = {
    content: [
        "./frontend/templates/**/*.html",
        "./frontend/static/js/**/*.js",
        "./frontend/static/css/**/*.css"
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: '#6ee7b7',
                    50: '#e6fff8',
                    100: '#98f5e1',
                    200: '#6ee7b7',
                    300: '#47d6aa',
                    400: '#28c795',
                    500: '#10b981',
                    600: '#059669',
                    700: '#047857',
                    800: '#065f46',
                    900: '#064e3b'
                },
                gray: {
                    50: '#F9FAFB',
                    100: '#F3F4F6',
                    200: '#E5E7EB',
                    300: '#D1D5DB',
                    400: '#9CA3AF',
                    500: '#6B7280',
                    600: '#4B5563',
                    700: '#374151',
                    800: '#1F2937',
                    900: '#111827'
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif']
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-in-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'pulse-soft': 'pulseSoft 2s infinite',
                'bounce-soft': 'bounceSoft 1s infinite'
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' }
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' }
                },
                pulseSoft: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.8' }
                },
                bounceSoft: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-5px)' }
                }
            },
            minHeight: {
                '96': '24rem',
            },
            maxHeight: {
                '90vh': '90vh',
            }
        }
    },
    plugins: [],
}
