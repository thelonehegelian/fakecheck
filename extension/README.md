# FakeCheck Browser Extension

A Chrome extension for instant AI-powered fact-checking of claims on any webpage.

## Features

- 🔍 **Right-click Context Menu** - Select any text and fact-check it instantly
- 💡 **Popup Interface** - Paste text directly into the extension popup
- 🎯 **AI-Powered Analysis** - Uses Claude and Perplexity Sonar for comprehensive fact-checking
- 📊 **Detailed Results** - Shows ratings, confidence scores, risk factors, and sources
- ✅ **Verification Steps** - Get actionable steps to verify claims yourself

## Prerequisites

Before installing the extension, make sure:

1. **FakeCheck API is running** on `http://localhost:8000`
   ```bash
   cd backend
   doppler run -- python main.py
   # or
   doppler run -- uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **API is accessible** - Test with:
   ```bash
   curl http://localhost:8000/health
   ```

## Installation

### Chrome/Edge/Brave

1. **Create Icons** (temporary step until you have proper icons):
   - Create three simple PNG files in `extension/icons/`:
     - `icon16.png` (16x16 pixels)
     - `icon48.png` (48x48 pixels)
     - `icon128.png` (128x128 pixels)
   - Or use any online favicon generator and save as these names

2. **Load the Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top-right)
   - Click "Load unpacked"
   - Select the `extension/` folder
   - The FakeCheck extension should now appear in your extensions

3. **Pin the Extension** (optional):
   - Click the puzzle piece icon in Chrome toolbar
   - Find "FakeCheck - AI Fact Checker"
   - Click the pin icon to keep it visible

## Usage

### Method 1: Context Menu (Right-Click)

1. Select any text on a webpage
2. Right-click and choose "Fact-check this with FakeCheck"
3. The extension popup will open with results

### Method 2: Extension Popup

1. Click the FakeCheck icon in your toolbar
2. Paste or type text into the text area
3. Click "Check This Claim"
4. View the results

### Method 3: Keyboard Shortcut

- In the popup, press `Ctrl+Enter` (or `Cmd+Enter` on Mac) to submit

## Understanding Results

### Rating Scale (1-5)
- **1 - True ✅**: Claim is verified and accurate
- **2 - Likely True 🟢**: Claim is probably accurate with minor issues
- **3 - Unverified / Mixed 🟡**: Cannot be verified or has mixed evidence
- **4 - Likely Fake 🔴**: Claim is probably false or misleading
- **5 - Fake ❌**: Claim is definitely false

### Result Sections

- **Analysis**: Detailed explanation of why the claim is rated as it is
- **Risk Factors**: Warning signs or concerns about the claim
- **Sources**: Citations and references used in the analysis
- **Verification Steps**: Actionable steps you can take to verify the claim yourself
  - Easy (green): Quick checks you can do in minutes
  - Medium (orange): Moderate effort required
  - Hard (red): Complex verification requiring expertise

## Troubleshooting

### "Failed to check claim. Make sure the FakeCheck API is running..."

**Solution**:
- Ensure the backend server is running on `http://localhost:8000`
- Test the API: `curl http://localhost:8000/health`
- Check that you have API keys configured (see backend README)

### Extension doesn't appear after loading

**Solution**:
- Make sure you have the icon files in `extension/icons/`
- Check Chrome DevTools console for errors: Right-click extension > "Inspect popup"
- Try reloading the extension: `chrome://extensions/` > Click reload icon

### Context menu doesn't show

**Solution**:
- Right-click on the extension icon and select "Options" or "Manage"
- Remove and re-add the extension
- Make sure you've selected some text before right-clicking

### Results look broken or unstyled

**Solution**:
- Check that `styles.css` exists in the extension folder
- Inspect the popup (right-click extension > Inspect popup)
- Check for CSS errors in the console

## Development

### File Structure

```
extension/
├── manifest.json       # Extension configuration
├── popup.html          # Main UI
├── popup.js           # UI logic and API calls
├── styles.css         # Styling
├── background.js      # Service worker (context menu, etc.)
├── content.js         # Content script (runs on pages)
├── icons/             # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md          # This file
```

### Making Changes

After modifying any files:
1. Go to `chrome://extensions/`
2. Click the reload icon on the FakeCheck extension
3. Test your changes

### Debugging

- **Popup debugging**: Right-click extension icon > "Inspect popup"
- **Background script**: `chrome://extensions/` > Click "Inspect views: service worker"
- **Content script**: Open DevTools on any webpage (F12) and check console

## Future Enhancements

Potential features to add:

- [ ] Keyboard shortcuts for quick fact-checking
- [ ] History of checked claims
- [ ] Export results as PDF/text
- [ ] Highlight suspicious claims automatically on news sites
- [ ] Browser notifications for completed checks
- [ ] Support for checking images (OCR + fact-check)
- [ ] Support for checking URLs (scrape + fact-check)
- [ ] Dark mode
- [ ] Settings page for API endpoint configuration
- [ ] Firefox and Safari support

## API Configuration

By default, the extension connects to `http://localhost:8000`. To change this:

1. Edit `popup.js` and `background.js`
2. Update the API_URL or fetch URL to your server address
3. Update `manifest.json` `host_permissions` if using a different domain

## License

Part of the FakeCheck project.
