# ScholarForm AI - Frontend

This is the frontend application for ScholarForm AI, an automated academic manuscript formatter. It is built with [Next.js](https://nextjs.org/) (App Router), [React](https://react.dev/), and [Tailwind CSS](https://tailwindcss.com/).

## Architecture

The application uses the Next.js App Router for routing and layout.

### Directory Structure
- `app/`: Next.js App Router pages and layouts.
  - `(shared)`: Routes accessible in both formatter and generator modes.
  - `(formatter)`: Routes specific to the formatter functionality.
  - `(generator)`: Routes specific to the generator functionality.
- `src/components/`: Reusable React components.
  - `ui/`: Canonical Design System components (e.g., `Button`, `Input`, `ConfirmDialog`).
  - `layout/`: Layout components (e.g., `AppShell`, `Sidebar`, `Navbar`).
- `src/context/`: React Context providers for global state.
- `src/services/`: API integration and utility functions.
- `src/lib/`: Shared utilities and helpers.

## Design System

ScholarForm AI uses a unified design system built on top of Tailwind CSS. All components must adhere to the following standards:

### Colors
- **Primary**: A custom blue palette defined in `tailwind.config.ts`. Used for primary actions, active states, and highlights.
- **Accent**: A custom green palette (`#2d6a4f` base) used for secondary highlights and nature-themed accents.
- **Neutrals**: `slate-*` is the standard neutral color palette across the application. **Do not use `gray-*` or other neutral palettes.**
- **Glass**: Custom `glass-surface` and `glass-border` tokens are used for semi-transparent overlay components.

### Typography
- **Font**: Inter (`var(--font-inter)`) is the primary font family for both `font-sans` and `font-display`.
- **Weights**: Use standard font weights (`font-normal`, `font-medium`, `font-semibold`, `font-bold`).

### Components
All new UI components should be placed in `src/components/ui` and built using the `cn()` utility from `src/lib/utils.ts` (or `clsx`/`tailwind-merge` directly) to merge Tailwind classes efficiently.

Example usage:
```jsx
import { cn } from '@/src/lib/utils';

export function MyComponent({ className }) {
    return (
        <div className={cn("bg-white text-slate-900 rounded-xl", className)}>
            Content
        </div>
    );
}
```

### Accessibility (A11y)
- All interactive elements must have appropriate `aria-*` attributes (e.g., `aria-expanded`, `aria-describedby`, `aria-invalid`).
- Use semantic HTML elements whenever possible (`<button>`, `<nav>`, `<main>`, `<dialog>`).
- Ensure proper focus states are defined (`focus-visible:ring-2`).

## Styling Standards

- **Global Styles**: Defined in `app/globals.css`. It includes Tailwind directives, custom CSS variables, and global overrides (like custom scrollbars and animations).
- **No Inline Styles**: Avoid using inline styles. Rely on Tailwind utility classes.
- **Responsive Design**: Ensure components are fully responsive using Tailwind's `sm:`, `md:`, `lg:`, etc., breakpoints.

## Third-Party Libraries

- **Icons**: Lucide React and Material Symbols Outlined.
- **Toast Notifications**: Sonner (`toast.success('...')`, `toast.error('...')`). Always provide a descriptive message string. Do not use custom Toast implementations.
- **Animation**: Framer Motion is used for complex layout animations and transitions.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.
