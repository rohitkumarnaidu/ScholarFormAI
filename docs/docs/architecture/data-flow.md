# Data Flow

## Format Request Flow

```
User (UI/CLI/SDK)           API Gateway              Services              Storage
       │                        │                       │                     │
       │   POST /api/v1/format  │                       │                     │
       │───────────────────────▶│                       │                     │
       │                        │                       │                     │
       │                        │   Parse Manuscript    │                     │
       │                        │──────────────────────▶│                     │
       │                        │                       │                     │
       │                        │   Validate            │                     │
       │                        │──────────────────────▶│                     │
       │                        │                       │                     │
       │                        │   Format DOCX         │                     │
       │                        │──────────────────────▶│                     │
       │                        │                       │                     │
       │                        │   Save to Disk        │                     │
       │                        │────────────────────────────────────────────▶│
       │                        │                       │                     │
       │   200 OK + DOCX        │                       │                     │
       │◀───────────────────────│                       │                     │
       │                        │                       │                     │
```

## Validation Flow

```
User                          API                     Validator
  │                            │                         │
  │  POST /api/v1/validate     │                         │
  │───────────────────────────▶│                         │
  │                            │                         │
  │                            │  Validate Structure     │
  │                            │────────────────────────▶│
  │                            │                         │
  │                            │  Validate References    │
  │                            │────────────────────────▶│
  │                            │                         │
  │                            │  Validate Style Rules   │
  │                            │────────────────────────▶│
  │                            │                         │
  │  {valid, errors, warnings} │                         │
  │◀───────────────────────────│                         │
  │                            │                         │
```

## Preview Flow

```
User                          API                     Formatter
  │                            │                         │
  │  POST /api/v1/preview      │                         │
  │───────────────────────────▶│                         │
  │                            │                         │
  │                            │  Generate HTML          │
  │                            │────────────────────────▶│
  │                            │                         │
  │  {html: "<!DOCTYPE>..."}   │                         │
  │◀───────────────────────────│                         │
  │                            │                         │
```
