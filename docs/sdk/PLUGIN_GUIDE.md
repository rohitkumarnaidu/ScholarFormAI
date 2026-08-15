# Plugin Guide

ScholarFormAI supports a robust plugin architecture allowing developers to extend formatting capabilities, add new reference styles, or integrate with third-party tools.

## Architecture

Plugins run in an isolated environment during the document processing pipeline. You can hook into the following lifecycle events:

1. `onDocumentLoad`: Manipulate raw OOXML before formatting begins.
2. `beforeFormat`: Adjust the selected template or styles dynamically.
3. `onParagraphFormat`: Process individual paragraphs (e.g., custom regex replacements).
4. `onSave`: Post-process the generated file.

## Creating a Plugin

### 1. Initialization

Initialize a new plugin project:

```bash
scholarform plugin create my-custom-formatter
cd my-custom-formatter
npm install
```

### 2. Implementation

Implement the plugin hooks in `index.js`:

```javascript
module.exports = {
  name: 'my-custom-formatter',
  version: '1.0.0',
  
  hooks: {
    onParagraphFormat: (paragraph, context) => {
      // Example: Ensure all paragraphs containing "Warning:" are bolded
      if (paragraph.text.includes("Warning:")) {
        paragraph.applyStyle({ bold: true });
      }
      return paragraph;
    }
  }
};
```

### 3. Testing

Run the local plugin test suite:

```bash
scholarform plugin test
```

### 4. Publishing

Publish your plugin to the ScholarForm Registry:

```bash
scholarform plugin publish
```

## Security Guidelines

- Plugins must not attempt to access the host file system.
- Network requests are strictly disabled by default. If your plugin requires external API access, declare it in `plugin.json` under `permissions`.

## Read More

- [Developer Guide](../guides/DEVELOPER_GUIDE.md)
- [API Reference](../api/API_REFERENCE.md)
