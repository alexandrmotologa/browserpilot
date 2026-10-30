# Accessibility Tree Parsing and Grounding

BrowserPilot replaces raw DOM dumps and full-screen screenshots with structured accessibility tree snapshots. This approach provides clean semantic data while reducing LLM prompt token size by roughly 80%.

## The Accessibility Pipeline

```
+-----------------------------------------------------------+
| Chrome DevTools Protocol: Accessibility.getFullAXTree     |
+-----------------------------+-----------------------------+
                              |
                              v
+-----------------------------------------------------------+
| Filter Interactive Roles & Visible Nodes                  |
| - role in (button, link, textbox, combobox, checkbox...)  |
| - filter out hidden, collapsed, or 0x0 size elements      |
+-----------------------------+-----------------------------+
                              |
                              v
+-----------------------------------------------------------+
| Resolve Visual Viewport Coordinates                       |
| - getBoundingClientRect / DOM.getBoxModel                 |
| - assign sequential integer IDs: [1], [2], [3]            |
+-----------------------------+-----------------------------+
                              |
                              v
+-----------------------------------------------------------+
| Dual Output Generation:                                   |
| 1. Textual a11y prompt for LLM                            |
| 2. Ephemeral badge injection into page for live stream    |
+-----------------------------------------------------------+
```

## Tree Representation

Instead of feeding hundreds of nested `<div>` and `<span>` elements to the model, BrowserPilot emits a compact token-budgeted list:

```text
[1] link "Gmail" (x: 820, y: 18)
[2] link "Images" (x: 875, y: 18)
[3] button "Google apps" (x: 930, y: 18)
[4] combobox "Search" (x: 480, y: 310) [focused]
[5] button "Google Search" (x: 430, y: 395)
[6] button "I'm Feeling Lucky" (x: 550, y: 395)
```

Each line conveys:
- Element identifier `[id]`
- Role type (`button`, `link`, `combobox`, `checkbox`)
- Accessible name or label
- Visual center coordinates `(x, y)`
- Key state flags (`focused`, `disabled`, `checked`, `expanded`)

## Coordinate Mapping and Bounding Badges

To assist visual inspection and human verification, BrowserPilot injects an ephemeral badge script into the page.

Badges are rendered as small, absolute-positioned badges pinned to the top-left of each interactive element:
- Badge text corresponds directly to the numeric index `[id]`.
- Badges use contrasting colors with minimal dimensions so they do not block surrounding interactive targets.
- Coordinates are cached for the action executor, enabling direct clicks via `page.mouse.click(x, y)` without fragile XPath or CSS selectors.
