# Frontend Development

<cite>
**Referenced Files in This Document**
- [package.json](file://frontend/package.json)
- [next.config.mjs](file://frontend/next.config.mjs)
- [tailwind.config.js](file://frontend/tailwind.config.js)
- [RootLayout](file://frontend/app/layout.jsx)
- [ClientProviders](file://frontend/src/components/layout/ClientProviders.jsx)
- [AuthContext](file://frontend/src/context/AuthContext.jsx)
- [supabaseClient](file://frontend/src/lib/supabaseClient.js)
- [api.auth](file://frontend/src/services/api.auth.js)
- [api.core](file://frontend/src/services/api.core.js)
- [schemas](file://frontend/src/lib/schemas.js)
- [ErrorBoundary](file://frontend/src/components/ErrorBoundary.jsx)
- [useLivePreviewSocket](file://frontend/src/hooks/useLivePreviewSocket.js)
- [useSessionEventStream](file://frontend/src/hooks/useSessionEventStream.js)
- [useGeneratorSessionStream](file://frontend/src/hooks/useGeneratorSessionStream.js)
- [Button](file://frontend/src/components/ui/Button.jsx)
- [AuthCallback](file://frontend/app/(shared)/auth/callback/page.jsx)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive frontend development guidance for the Next.js 14 application. It covers the App Router structure, page organization, component architecture, state management patterns, UI component library, form handling, real-time features, API integration strategies, authentication flow, context providers, React Query integration, and error boundary handling. It also includes component composition patterns, styling approaches with TailwindCSS, responsive design considerations, performance optimization techniques, accessibility compliance, cross-browser compatibility, and guidelines for extending the UI and adding new features.

## Project Structure
The frontend is organized under the Next.js App Router with route groups and shared pages. Key areas:
- app/: App Router pages and route groups for shared, formatter, and generator sections
- src/components/: Shared UI components and layout providers
- src/context/: Application-wide contexts (Auth, Theme, Toast, Document)
- src/hooks/: Custom hooks for real-time streams and uploads
- src/services/: API service modules for auth, core, documents, generation, and metrics
- src/lib/: Utility libraries (schemas, Supabase client, analytics)
- Styles: TailwindCSS configuration and global CSS

```mermaid
graph TB
subgraph "App Router"
A["app/layout.jsx<br/>Root layout and metadata"]
B["app/(shared)/...<br/>Shared routes (auth, terms, privacy)"]
C["app/(formatter)/...<br/>Formatter features (upload, edit, preview, results)"]
D["app/(generator)/...<br/>Generator features (synthesis, generation)"]
end
subgraph "Providers"
P1["src/components/layout/ClientProviders.jsx<br/>React Query, Theme, Toast, Auth, Document"]
end
subgraph "Contexts"
X1["src/context/AuthContext.jsx"]
X2["src/context/ThemeContext.jsx"]
X3["src/context/ToastContext.jsx"]
X4["src/context/DocumentContext.jsx"]
end
subgraph "Services"
S1["src/services/api.auth.js"]
S2["src/services/api.core.js"]
S3["src/services/api.*.js"]
end
subgraph "Libraries"
L1["src/lib/schemas.js"]
L2["src/lib/supabaseClient.js"]
L3["src/lib/ReconnectingWebSocket.js"]
end
A --> P1
P1 --> X1
P1 --> X2
P1 --> X3
P1 --> X4
X1 --> S1
X1 --> S2
S2 --> S3
L1 --> S2
L2 --> X1
```

**Diagram sources**
- [RootLayout:32-83](file://frontend/app/layout.jsx#L32-L83)
- [ClientProviders:14-50](file://frontend/src/components/layout/ClientProviders.jsx#L14-L50)
- [AuthContext:16-339](file://frontend/src/context/AuthContext.jsx#L16-L339)
- [api.auth:1-39](file://frontend/src/services/api.auth.js#L1-L39)
- [api.core:1-368](file://frontend/src/services/api.core.js#L1-L368)
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)
- [schemas:1-235](file://frontend/src/lib/schemas.js#L1-L235)

**Section sources**
- [RootLayout:1-84](file://frontend/app/layout.jsx#L1-L84)
- [ClientProviders:1-51](file://frontend/src/components/layout/ClientProviders.jsx#L1-L51)

## Core Components
- Root layout and metadata define fonts, theme color, OpenGraph/Twitter metadata, and accessibility skip link.
- ClientProviders initializes React Query, theme, toast, auth, document contexts, and analytics on route changes.
- AuthContext manages user session lifecycle, OTP flows, password reset, and Supabase integration with guarded auth state changes.
- Supabase client is conditionally exported based on environment variables to prevent SSR crashes.
- API core encapsulates request ID generation, sanitized payloads, retry logic, friendly error messages, and auth header injection.
- Real-time hooks support SSE-based event streams and WebSocket-based live preview with reconnection and debounced updates.

**Section sources**
- [RootLayout:12-83](file://frontend/app/layout.jsx#L12-L83)
- [ClientProviders:14-50](file://frontend/src/components/layout/ClientProviders.jsx#L14-L50)
- [AuthContext:16-339](file://frontend/src/context/AuthContext.jsx#L16-L339)
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)
- [api.core:1-368](file://frontend/src/services/api.core.js#L1-L368)
- [useSessionEventStream:1-101](file://frontend/src/hooks/useSessionEventStream.js#L1-L101)
- [useLivePreviewSocket:1-137](file://frontend/src/hooks/useLivePreviewSocket.js#L1-L137)

## Architecture Overview
The frontend follows a layered architecture:
- Presentation Layer: App Router pages and UI components
- Provider Layer: ClientProviders composes contexts and React Query
- Services Layer: API modules encapsulate HTTP calls and retry logic
- Utilities Layer: Zod schemas, Supabase client, analytics, and helpers
- Real-time Layer: SSE and WebSocket integrations for streaming synthesis and live preview

```mermaid
graph TB
UI["UI Pages and Components<br/>app/(formatter), app/(generator), app/(shared)"]
CP["ClientProviders<br/>React Query, Theme, Toast, Auth, Document"]
AC["AuthContext<br/>User state, OTP, reset, Supabase events"]
SC["Supabase Client<br/>SSR-safe client creation"]
AE["api.auth.js<br/>Signup, login, OTP, Google OAuth"]
CO["api.core.js<br/>Fetch with retry, auth headers, friendly errors"]
GS["useSessionEventStream.js<br/>SSE for synthesis/generation"]
LW["useLivePreviewSocket.js<br/>WebSocket for live HTML preview"]
UI --> CP
CP --> AC
AC --> SC
AC --> AE
AE --> CO
CO --> |"HTTP"| Backend["Backend API"]
GS --> |"SSE"| Backend
LW --> |"WS"| Backend
```

**Diagram sources**
- [RootLayout:32-83](file://frontend/app/layout.jsx#L32-L83)
- [ClientProviders:14-50](file://frontend/src/components/layout/ClientProviders.jsx#L14-L50)
- [AuthContext:16-339](file://frontend/src/context/AuthContext.jsx#L16-L339)
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)
- [api.auth:1-39](file://frontend/src/services/api.auth.js#L1-L39)
- [api.core:1-368](file://frontend/src/services/api.core.js#L1-L368)
- [useSessionEventStream:1-101](file://frontend/src/hooks/useSessionEventStream.js#L1-L101)
- [useLivePreviewSocket:1-137](file://frontend/src/hooks/useLivePreviewSocket.js#L1-L137)

## Detailed Component Analysis

### Authentication Flow and Context Providers
The authentication system integrates Supabase with a custom AuthContext to manage user state, OTP flows, and password resets. It listens to Supabase auth state changes, guards against race conditions during sign-in, and synchronizes local and Supabase storage.

```mermaid
sequenceDiagram
participant U as "User"
participant UI as "Auth UI"
participant AC as "AuthContext"
participant SB as "Supabase Client"
participant AE as "api.auth.js"
participant BE as "Backend"
U->>UI : "Submit login/signup"
UI->>AE : "Call login/signup"
AE->>BE : "POST /api/auth/*"
BE-->>AE : "Session tokens"
AE-->>AC : "Return session data"
AC->>SB : "setSession(access_token, refresh_token)"
SB-->>AC : "onAuthStateChange(SIGNED_IN)"
AC-->>UI : "isLoggedIn=true, user updated"
```

**Diagram sources**
- [AuthContext:180-249](file://frontend/src/context/AuthContext.jsx#L180-L249)
- [api.auth:18-26](file://frontend/src/services/api.auth.js#L18-L26)
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)

**Section sources**
- [AuthContext:16-339](file://frontend/src/context/AuthContext.jsx#L16-L339)
- [api.auth:1-39](file://frontend/src/services/api.auth.js#L1-L39)
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)
- [AuthCallback](file://frontend/app/(shared)/auth/callback/page.jsx#L1-L121)

### Real-Time Features: SSE Streams and WebSocket Live Preview
Two real-time mechanisms are implemented:
- SSE-based synthesis/generation streams via useSessionEventStream
- WebSocket-based live preview via useLivePreviewSocket with exponential backoff and debounced content sending

```mermaid
sequenceDiagram
participant UI as "UI Component"
participant SSE as "useSessionEventStream"
participant SB as "Supabase Session"
participant BE as "Backend SSE Endpoint"
UI->>SSE : "Provide sessionId and getEventsUrl()"
SSE->>SB : "Get access_token"
SSE->>BE : "Open EventSource with token"
BE-->>SSE : "Send stage progress events"
SSE-->>UI : "Update stages, progress, completion"
```

**Diagram sources**
- [useSessionEventStream:1-101](file://frontend/src/hooks/useSessionEventStream.js#L1-L101)

```mermaid
sequenceDiagram
participant UI as "Editor Component"
participant WS as "useLivePreviewSocket"
participant RWS as "ReconnectingWebSocket"
participant BE as "Backend WebSocket /api/v1/ws/preview/{id}"
UI->>WS : "sendContent(content, templateId)"
WS->>RWS : "Debounced payload with checksum"
RWS->>BE : "Send JSON payload"
BE-->>RWS : "HTML + warnings"
RWS-->>WS : "onmessage(html, warnings)"
WS-->>UI : "Render live preview"
```

**Diagram sources**
- [useLivePreviewSocket:1-137](file://frontend/src/hooks/useLivePreviewSocket.js#L1-L137)

**Section sources**
- [useSessionEventStream:1-101](file://frontend/src/hooks/useSessionEventStream.js#L1-L101)
- [useGeneratorSessionStream:1-12](file://frontend/src/hooks/useGeneratorSessionStream.js#L1-L12)
- [useLivePreviewSocket:1-137](file://frontend/src/hooks/useLivePreviewSocket.js#L1-L137)

### Form Handling and Validation
Form validation leverages Zod schemas for robust client-side validation aligned with backend expectations. Schemas cover user profiles, authentication, settings, uploads, feedback, agent sessions, synthesis sessions, and generator requests.

```mermaid
flowchart TD
Start(["Form Submission"]) --> Validate["Validate with Zod Schema"]
Validate --> Valid{"Valid?"}
Valid --> |No| ShowErrors["Show field-specific errors"]
Valid --> |Yes| Sanitize["Sanitize Payload"]
Sanitize --> CallAPI["Call API Service"]
CallAPI --> HandleResponse["Handle Success/Error"]
ShowErrors --> End(["Stop"])
HandleResponse --> End
```

**Diagram sources**
- [schemas:1-235](file://frontend/src/lib/schemas.js#L1-L235)
- [api.core:60-83](file://frontend/src/services/api.core.js#L60-L83)

**Section sources**
- [schemas:1-235](file://frontend/src/lib/schemas.js#L1-L235)
- [api.core:60-83](file://frontend/src/services/api.core.js#L60-L83)

### API Integration Strategies
The API layer centralizes:
- Request ID generation for tracing
- Sanitized payloads to mitigate XSS/control chars
- Retry logic for safe HTTP methods and specific status codes
- Friendly error messages mapped from network, server, and auth errors
- Auth header injection using Supabase session with graceful fallback

```mermaid
flowchart TD
A["fetchWithAuth(endpoint, options)"] --> B["withAuthHeader()<br/>Inject X-Request-Id + Bearer token"]
B --> C["fetchWithRetry()<br/>Exponential backoff for GET/HEAD/OPTIONS"]
C --> D{"response.ok?"}
D --> |Yes| E["parseResponseData()<br/>JSON or raw text"]
D --> |No| F["getFriendlyErrorMessage()<br/>Map status/network/auth"]
F --> G["Optionally log to backend metrics"]
G --> H["Throw user-friendly error"]
E --> I["Return data"]
```

**Diagram sources**
- [api.core:190-362](file://frontend/src/services/api.core.js#L190-L362)

**Section sources**
- [api.core:1-368](file://frontend/src/services/api.core.js#L1-L368)

### UI Component Library and Composition Patterns
The UI library emphasizes composability and consistency:
- Button component supports variants, sizes, loading states, and disabled states
- Composition pattern: wrap child components in providers to share state and services
- Tailwind utilities enable responsive design and theme-aware styling

```mermaid
classDiagram
class Button {
+variant : "primary|secondary|danger"
+size : "sm|md|lg"
+loading : boolean
+disabled : boolean
+children : ReactNode
}
```

**Diagram sources**
- [Button:23-57](file://frontend/src/components/ui/Button.jsx#L23-L57)

**Section sources**
- [Button:1-58](file://frontend/src/components/ui/Button.jsx#L1-L58)
- [ClientProviders:14-50](file://frontend/src/components/layout/ClientProviders.jsx#L14-L50)

### Error Boundary Handling
The ErrorBoundary component captures rendering errors, logs them to backend metrics, and offers user actions to retry or reload.

```mermaid
sequenceDiagram
participant React as "React Renderer"
participant EB as "ErrorBoundary"
participant Log as "logFrontendError"
React->>EB : "Render child"
EB-->>React : "Child renders"
React->>EB : "Error thrown"
EB->>Log : "Send error info"
Log-->>EB : "Logged"
EB-->>React : "Show friendly UI with Retry/Reload"
```

**Diagram sources**
- [ErrorBoundary:1-91](file://frontend/src/components/ErrorBoundary.jsx#L1-L91)

**Section sources**
- [ErrorBoundary:1-91](file://frontend/src/components/ErrorBoundary.jsx#L1-L91)

## Dependency Analysis
External dependencies and build optimizations:
- Next.js 16 with Sentry integration and Turbopack dev mode
- React Query for caching and background synchronization
- Supabase for auth and SSR-safe client creation
- TailwindCSS with form and container query plugins
- Tooling: Playwright for E2E, Vitest for unit tests, ESLint for linting

```mermaid
graph LR
N["Next.js 16"]
RQ["@tanstack/react-query"]
SB["@supabase/supabase-js"]
TW["TailwindCSS"]
PH["PostHog"]
SE["@sentry/nextjs"]
N --> RQ
N --> SB
N --> TW
N --> PH
N --> SE
```

**Diagram sources**
- [package.json:17-36](file://frontend/package.json#L17-L36)
- [next.config.mjs:1-27](file://frontend/next.config.mjs#L1-L27)
- [tailwind.config.js:1-55](file://frontend/tailwind.config.js#L1-L55)

**Section sources**
- [package.json:1-62](file://frontend/package.json#L1-L62)
- [next.config.mjs:1-27](file://frontend/next.config.mjs#L1-L27)
- [tailwind.config.js:1-55](file://frontend/tailwind.config.js#L1-L55)

## Performance Considerations
- React Query defaults: short stale time, limited retries, window focus refetch disabled to reduce unnecessary network calls
- Optimizations: tree-shake heavy packages, optimize package imports for lucide-react and react-query
- Build: Sentry configuration with treeshaking and debug logging removal
- Real-time: Debounced WebSocket sends, exponential backoff, and SSE retry with capped attempts
- Accessibility: Skip-to-main-content link, semantic markup, and focus management via FocusManager

**Section sources**
- [ClientProviders:16-24](file://frontend/src/components/layout/ClientProviders.jsx#L16-L24)
- [next.config.mjs:7-11](file://frontend/next.config.mjs#L7-L11)
- [useLivePreviewSocket:48-102](file://frontend/src/hooks/useLivePreviewSocket.js#L48-L102)
- [useSessionEventStream:20-97](file://frontend/src/hooks/useSessionEventStream.js#L20-L97)

## Troubleshooting Guide
Common issues and resolutions:
- Supabase environment variables missing: client is null; guard all Supabase-dependent code
- Auth race conditions: signingInRef prevents clearing state during sign-in/sign-up
- Network errors: friendly messages map to user-friendly strings; inspect status codes and retry behavior
- Real-time connectivity: SSE and WebSocket implement retry/backoff; monitor reconnectAttempt and isReconnecting
- Error boundaries: use Retry/Reload buttons; backend error logs are sent for diagnostics

**Section sources**
- [supabaseClient:1-24](file://frontend/src/lib/supabaseClient.js#L1-L24)
- [AuthContext:23-23](file://frontend/src/context/AuthContext.jsx#L23-L23)
- [api.core:85-188](file://frontend/src/services/api.core.js#L85-L188)
- [useLivePreviewSocket:91-102](file://frontend/src/hooks/useLivePreviewSocket.js#L91-L102)
- [useSessionEventStream:76-97](file://frontend/src/hooks/useSessionEventStream.js#L76-L97)
- [ErrorBoundary:20-30](file://frontend/src/components/ErrorBoundary.jsx#L20-L30)

## Conclusion
The frontend leverages Next.js 14’s App Router, a layered provider architecture, robust API integration with retry and sanitization, and real-time capabilities via SSE and WebSocket. The design emphasizes accessibility, responsive styling with TailwindCSS, and maintainability through Zod schemas and context providers. Extending the UI and adding features should follow established patterns: compose providers, use Zod schemas for validation, integrate APIs via api.core, and implement real-time features with the existing hooks.

## Appendices

### Styling Approaches with TailwindCSS
- Dark mode via class strategy
- Extended theme: custom colors, border radius, transition timing, and display font
- Plugins: forms and container queries
- Global styles: background and text color classes applied at the root body

**Section sources**
- [tailwind.config.js:1-55](file://frontend/tailwind.config.js#L1-L55)
- [RootLayout:61-83](file://frontend/app/layout.jsx#L61-L83)

### Responsive Design Considerations
- Mobile-first approach with Tailwind utilities
- Container queries enabled for flexible layouts
- Accessible focus styles and skip links for keyboard navigation

**Section sources**
- [tailwind.config.js:1-55](file://frontend/tailwind.config.js#L1-L55)
- [RootLayout:71-76](file://frontend/app/layout.jsx#L71-L76)

### Cross-Browser Compatibility
- UUID generation falls back to Math.random() when crypto.randomUUID is unavailable
- WebSocket and EventSource supported across modern browsers; reconnect logic accommodates flaky connections

**Section sources**
- [api.core:21-30](file://frontend/src/services/api.core.js#L21-L30)
- [useLivePreviewSocket:48-102](file://frontend/src/hooks/useLivePreviewSocket.js#L48-L102)
- [useSessionEventStream:38-87](file://frontend/src/hooks/useSessionEventStream.js#L38-L87)

### Guidelines for Extending the UI and Adding New Features
- Add new pages under the appropriate route group (shared/formatter/generator) following the existing patterns
- Wrap new pages/components with ClientProviders to access contexts and React Query
- Define Zod schemas for new forms and reuse sanitizePayload for consistent data hygiene
- Integrate with api.core for HTTP calls; leverage fetchWithRetry and friendly error messages
- For real-time features, choose SSE via useSessionEventStream or WebSocket via useLivePreviewSocket depending on backend endpoints
- Maintain accessibility: semantic HTML, ARIA attributes, focus management, and keyboard navigation
- Keep styling consistent with Tailwind utilities and theme tokens

**Section sources**
- [ClientProviders:14-50](file://frontend/src/components/layout/ClientProviders.jsx#L14-L50)
- [schemas:1-235](file://frontend/src/lib/schemas.js#L1-L235)
- [api.core:190-362](file://frontend/src/services/api.core.js#L190-L362)
- [useSessionEventStream:1-101](file://frontend/src/hooks/useSessionEventStream.js#L1-L101)
- [useLivePreviewSocket:1-137](file://frontend/src/hooks/useLivePreviewSocket.js#L1-L137)