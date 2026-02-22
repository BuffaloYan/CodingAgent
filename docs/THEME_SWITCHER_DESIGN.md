# UI Theme Switcher

The objective is to introduce a theme switcher in the top-right corner to allow selecting between Dark, Grey, White (Light), and System Default. The current UI is hardcoded to be dark.

## Proposed Changes

### 1. Refactor CSS and JS in `app.py`
- Modify `CUSTOM_CSS` to define CSS variables for three themes: `dark`, `grey`, and `light`.
- Have the `body`, `.gradio-container`, and `#app-header` use these CSS variables.
- Update `app.py`'s `#app-header` HTML to include a `<select id="theme-select">` positioned to the left of the maximize button.
- Update `CUSTOM_JS` to load the saved theme from `localStorage` on load, apply the `data-theme` attribute to `document.documentElement`, and toggle Gradio's internal `dark` class.

### 2. Update `workspace_tab.py` previews
- Many of the HTML builders in `_build_preview` use hardcoded dark colors (e.g., `#1e1e2e`, `#313244`). We will update these components to adapt better to light mode, either by injecting the CSS variables or modifying their styles. 

## Verification Plan

### Manual Verification
- Run the application (`make run`).
- Verify the dropdown appears in the top-right corner.
- Select "White" and verify the wrapper UI and Gradio elements adapt to a light scheme.
- Verify "Grey" provides a mid-tone scheme.
- Verify "System Default" follows the OS color scheme.
