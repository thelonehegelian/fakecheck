// DOM Elements
const textInput = document.getElementById('textInput');
const checkBtn = document.getElementById('checkBtn');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');
const newCheckBtn = document.getElementById('newCheckBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const settingsError = document.getElementById('settingsError');
const apiUrlInput = document.getElementById('apiUrlInput');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');

// New DOM Elements for tabs & images
const tabText = document.getElementById('tabText');
const tabImage = document.getElementById('tabImage');
const textInputSection = document.getElementById('textInputSection');
const imageInputSection = document.getElementById('imageInputSection');
const imageDropZone = document.getElementById('imageDropZone');
const imageFileInput = document.getElementById('imageFileInput');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imagePreview = document.getElementById('imagePreview');
const clearImageBtn = document.getElementById('clearImageBtn');
const imageFileInfo = document.getElementById('imageFileInfo');
const checkImageBtn = document.getElementById('checkImageBtn');
const transcriptionSection = document.getElementById('transcriptionSection');
const transcriptionText = document.getElementById('transcriptionText');

let currentImageBase64 = null; // Store base64 data URL of selected image

// Rating mapping
const ratingMap = {
  1: { text: 'True ✅', class: 'rating-1' },
  2: { text: 'Likely True 🟢', class: 'rating-2' },
  3: { text: 'Unverified / Mixed 🟡', class: 'rating-3' },
  4: { text: 'Likely Fake 🔴', class: 'rating-4' },
  5: { text: 'Fake ❌', class: 'rating-5' }
};

// Complexity mapping
const complexityMap = {
  'easy': 'Easy',
  'medium': 'Medium',
  'hard': 'Hard'
};

// Format analysis text with proper HTML formatting
function formatAnalysisText(text) {
  if (!text) return 'No analysis available.';

  // Split by lines
  let lines = text.split('\n');
  let formattedHtml = '';
  let inList = false;

  lines.forEach(line => {
    line = line.trim();
    if (!line) {
      // Empty line - close list if open and add paragraph break
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += '<br>';
      return;
    }

    // Check if line starts with a bullet point (-, *, •, or numbered)
    if (line.match(/^[-*•]\s/) || line.match(/^\d+\.\s/)) {
      if (!inList) {
        formattedHtml += '<ul>';
        inList = true;
      }
      // Remove the bullet/number and add as list item
      const content = line.replace(/^[-*•]\s/, '').replace(/^\d+\.\s/, '');
      formattedHtml += `<li>${escapeHtml(content)}</li>`;
    } else {
      // Regular text
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += `<p>${escapeHtml(line)}</p>`;
    }
  });

  // Close list if still open
  if (inList) {
    formattedHtml += '</ul>';
  }

  return formattedHtml || escapeHtml(text);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Initialize
// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Check if there's text from context menu
  chrome.storage.local.get(['selectedText'], (data) => {
    if (data.selectedText) {
      textInput.value = data.selectedText;
      // Clear the storage
      chrome.storage.local.remove(['selectedText']);

      // Select text tab
      tabText.classList.add('active');
      tabImage.classList.remove('active');
      textInputSection.classList.remove('hidden');
      imageInputSection.classList.add('hidden');

      // Auto-check if text is present
      if (data.selectedText.trim()) {
        checkClaim(data.selectedText);
      }
    }
  });

  // Tab switching
  tabText.addEventListener('click', () => {
    tabText.classList.add('active');
    tabImage.classList.remove('active');
    textInputSection.classList.remove('hidden');
    imageInputSection.classList.add('hidden');
    textInput.focus();
  });

  tabImage.addEventListener('click', () => {
    tabImage.classList.add('active');
    tabText.classList.remove('active');
    imageInputSection.classList.remove('hidden');
    textInputSection.classList.add('hidden');
  });

  // Drag and drop events for image
  imageDropZone.addEventListener('click', () => {
    imageFileInput.click();
  });

  imageFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      handleImageFile(file);
    }
  });

  imageDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDropZone.classList.add('dragover');
  });

  imageDropZone.addEventListener('dragleave', () => {
    imageDropZone.classList.remove('dragover');
  });

  imageDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      handleImageFile(file);
    }
  });

  // Clipboard paste handler
  document.addEventListener('paste', (e) => {
    if (tabImage.classList.contains('active')) {
      const items = e.clipboardData.items;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
          const file = items[i].getAsFile();
          handleImageFile(file);
          break;
        }
      }
    }
  });

  // Clear image action
  clearImageBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Avoid triggering dropzone click
    resetImagePreview();
  });

  // Check image claim action
  checkImageBtn.addEventListener('click', () => {
    if (currentImageBase64) {
      checkImageClaim(currentImageBase64);
    }
  });

  function handleImageFile(file) {
    if (!file.type.match('image.*')) {
      alert('Please select a valid image file (PNG, JPEG, WebP, GIF).');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('Image size exceeds 5MB limit.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      currentImageBase64 = e.target.result;
      imagePreview.src = currentImageBase64;
      imageFileInfo.textContent = `${file.name} (${formatBytes(file.size)})`;
      imagePreviewContainer.classList.remove('hidden');
      imageDropZone.classList.add('hidden');
      checkImageBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  // Button event listeners
  checkBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (text) {
      checkClaim(text);
    }
  });

  retryBtn.addEventListener('click', resetUI);
  newCheckBtn.addEventListener('click', resetUI);

  // Enter key to submit
  textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      checkBtn.click();
    }
  });

  // Settings toggle
  settingsBtn.addEventListener('click', () => {
    chrome.storage.local.get(['apiUrl'], (data) => {
      apiUrlInput.value = data.apiUrl || 'https://backend-production-2f0a.up.railway.app';
      settingsPanel.classList.toggle('hidden');
      clearSettingsError();
    });
  });

  // Save Settings
  saveSettingsBtn.addEventListener('click', () => {
    let url = apiUrlInput.value.trim();
    if (!url) {
      url = 'https://backend-production-2f0a.up.railway.app';
    }
    // Remove trailing slash if present
    if (url.endsWith('/')) {
      url = url.slice(0, -1);
    }

    // Strictly validate URL to mitigate security risks (B2)
    try {
      const parsedUrl = new URL(url);
      const protocol = parsedUrl.protocol;
      const hostname = parsedUrl.hostname;

      if (protocol === 'http:') {
        // Restrict HTTP only to localhost and 127.0.0.1 loopbacks
        if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
          showSettingsError('HTTP is only allowed for localhost development. Use HTTPS for remote backends.');
          return;
        }
      } else if (protocol !== 'https:') {
        showSettingsError('Only HTTP (localhost only) or HTTPS protocols are supported.');
        return;
      }
    } catch (e) {
      showSettingsError('Please enter a valid absolute URL (e.g. http://localhost:8000 or https://your-app.up.railway.app).');
      return;
    }

    chrome.storage.local.set({ apiUrl: url }, () => {
      settingsPanel.classList.add('hidden');
      clearSettingsError();
    });
  });

  // Close Settings
  closeSettingsBtn.addEventListener('click', () => {
    settingsPanel.classList.add('hidden');
    clearSettingsError();
  });

  // Helpers to manage settings error display
  function showSettingsError(message) {
    settingsError.textContent = message;
    settingsError.classList.remove('hidden');
  }

  function clearSettingsError() {
    settingsError.textContent = '';
    settingsError.classList.add('hidden');
  }
});

// Reset UI to initial state
function resetUI() {
  hideAll();

  if (tabText.classList.contains('active')) {
    textInputSection.classList.remove('hidden');
    textInput.value = '';
    textInput.focus();
  } else {
    imageInputSection.classList.remove('hidden');
    resetImagePreview();
  }
}

// Hide all sections
function hideAll() {
  textInputSection.classList.add('hidden');
  imageInputSection.classList.add('hidden');
  loading.classList.add('hidden');
  results.classList.add('hidden');
  error.classList.add('hidden');
}

// Clear image preview helper
function resetImagePreview() {
  currentImageBase64 = null;
  imagePreview.src = '';
  imageFileInput.value = '';
  imageFileInfo.textContent = '';
  imagePreviewContainer.classList.add('hidden');
  imageDropZone.classList.remove('hidden');
  checkImageBtn.disabled = true;
}

// Format bytes helper
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Main function to check claim from image
async function checkImageClaim(imageBase64) {
  showLoading();

  let baseUrl = DEFAULT_API_URL;
  try {
    baseUrl = await getApiUrl();
    const response = await fetch(`${baseUrl}/v1/check-image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image: imageBase64 })
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Check if there's an error in the response
    if (data.error) {
      throw new Error(data.error);
    }

    showResults(data);

  } catch (err) {
    console.error('Error checking image claim:', err);
    let message = 'Failed to check image claim. ';

    if (err.message.includes('Failed to fetch')) {
      message += `Make sure the FakeCheck API is running on ${baseUrl}`;
    } else {
      message += err.message;
    }

    showError(message);
  }
}

// Show loading state
function showLoading() {
  hideAll();
  loading.classList.remove('hidden');
}

// Show error state
function showError(message) {
  hideAll();
  error.classList.remove('hidden');
  errorMessage.textContent = message;
}

// Show results
function showResults(data) {
  hideAll();
  results.classList.remove('hidden');

  // Display rating
  const rating = data.fake_news_rating || 3;
  const ratingBadge = document.getElementById('ratingBadge');
  const ratingInfo = ratingMap[rating] || ratingMap[3];
  ratingBadge.textContent = ratingInfo.text;
  ratingBadge.className = `rating-badge ${ratingInfo.class}`;

  // Display confidence
  const confidence = data.confidence_score || 0;
  document.getElementById('confidence').textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;

  // Display image transcription if present
  if (data.image_transcription) {
    transcriptionSection.classList.remove('hidden');
    transcriptionText.textContent = data.image_transcription;
  } else {
    transcriptionSection.classList.add('hidden');
  }

  // Display analysis
  const analysis = data.fake_news_explanation || data.true_news_explanation || 'No analysis available.';
  document.getElementById('analysis').innerHTML = formatAnalysisText(analysis);

  // Display risk factors
  const riskFactors = data.risk_factors || [];
  const riskSection = document.getElementById('riskSection');
  const riskList = document.getElementById('riskFactors');
  if (riskFactors.length > 0) {
    riskSection.style.display = 'block';
    riskList.innerHTML = riskFactors.map(factor => `<li>${escapeHtml(factor)}</li>`).join('');
  } else {
    riskSection.style.display = 'none';
  }

  // Display sources
  const citations = data.citations || [];
  const sourcesSection = document.getElementById('sourcesSection');
  const sourcesList = document.getElementById('sources');
  if (citations.length > 0) {
    sourcesSection.style.display = 'block';
    sourcesList.innerHTML = citations.map((cite, i) => {
      if (typeof cite === 'string') {
        return `<div class="source-item">${i + 1}. ${escapeHtml(cite)}</div>`;
      } else if (cite.url) {
        const safeUrl = cite.url.startsWith('http') ? cite.url : '#';
        return `<div class="source-item">${i + 1}. <a href="${safeUrl}" target="_blank">${escapeHtml(cite.title || 'Source')}</a></div>`;
      }
      return '';
    }).join('');
  } else {
    sourcesSection.style.display = 'none';
  }

  // Display verification steps
  const steps = data.verification_steps || [];
  const stepsSection = document.getElementById('stepsSection');
  const stepsList = document.getElementById('verificationSteps');
  if (steps.length > 0) {
    stepsSection.style.display = 'block';
    stepsList.innerHTML = steps.map((step, i) => {
      const complexity = step.complexity || 'medium';
      const complexityLabel = complexityMap[complexity.toLowerCase()] || complexity;
      const stepText = step.step || step.description || (typeof step === 'string' ? step : '');
      const time = step.estimated_time || '';
      return `
        <div class="step-item">
          <strong>${i + 1}. ${escapeHtml(stepText)}</strong>
          <span class="step-complexity complexity-${complexity.toLowerCase()}">${escapeHtml(complexityLabel)}</span>
          ${time ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">⏱️ ${escapeHtml(time)}</div>` : ''}
        </div>
      `;
    }).join('');
  } else {
    stepsSection.style.display = 'none';
  }
}

// Main function to check claim
async function checkClaim(text) {
  showLoading();

  let baseUrl = DEFAULT_API_URL;
  try {
    baseUrl = await getApiUrl();
    const response = await fetch(`${baseUrl}/v1/check-fake`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ news: text })
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Check if there's an error in the response
    if (data.error) {
      throw new Error(data.error);
    }

    showResults(data);

  } catch (err) {
    console.error('Error checking claim:', err);
    let message = 'Failed to check claim. ';

    if (err.message.includes('Failed to fetch')) {
      message += `Make sure the FakeCheck API is running on ${baseUrl}`;
    } else {
      message += err.message;
    }

    showError(message);
  }
}
