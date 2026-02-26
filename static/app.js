// Photo Styling App - Frontend JavaScript

const form = document.getElementById('transformForm');
const formView = document.getElementById('formView');
const resultsView = document.getElementById('resultsView');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const submitBtn = document.getElementById('submitBtn');

// Camera and image elements
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const previewImage = document.getElementById('previewImage');
const previewContainer = document.getElementById('previewContainer');
const noImageMessage = document.getElementById('noImageMessage');
const fileInput = document.getElementById('fileInput');

// Buttons
const startCameraBtn = document.getElementById('startCameraBtn');
const captureBtn = document.getElementById('captureBtn');
const stopCameraBtn = document.getElementById('stopCameraBtn');
const clearImageBtn = document.getElementById('clearImageBtn');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');
const startOverBtn = document.getElementById('startOverBtn');

// State
let stream = null;
let currentImageBlob = null;
let currentImageData = null;

// Camera functionality
startCameraBtn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } }
        });
        video.srcObject = stream;
        video.style.display = 'block';
        previewContainer.style.display = 'none';
        startCameraBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';
        stopCameraBtn.style.display = 'inline-block';
    } catch (err) {
        showError('Could not access camera: ' + err.message);
    }
});

stopCameraBtn.addEventListener('click', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    video.style.display = 'none';
    previewContainer.style.display = 'flex';
    startCameraBtn.style.display = 'inline-block';
    captureBtn.style.display = 'none';
    stopCameraBtn.style.display = 'none';
});

captureBtn.addEventListener('click', () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
        setImage(blob);
        stopCameraBtn.click(); // Stop camera after capture
    }, 'image/jpeg', 0.9);
});

// File upload
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        setImage(file);
    }
});

// Clear image
clearImageBtn.addEventListener('click', () => {
    currentImageBlob = null;
    currentImageData = null;
    previewImage.style.display = 'none';
    noImageMessage.style.display = 'block';
    clearImageBtn.style.display = 'none';
    updateSubmitButton();
});

function setImage(blob) {
    currentImageBlob = blob;
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImageData = e.target.result;
        previewImage.src = currentImageData;
        previewImage.style.display = 'block';
        noImageMessage.style.display = 'none';
        clearImageBtn.style.display = 'inline-block';
        updateSubmitButton();
    };
    reader.readAsDataURL(blob);
}

function updateSubmitButton() {
    const theme = document.getElementById('themeSelect').value;
    submitBtn.disabled = !(theme && currentImageBlob);
}

document.getElementById('themeSelect').addEventListener('change', updateSubmitButton);

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!currentImageBlob) {
        showError('Please capture or upload an image');
        return;
    }
    
    const theme = document.getElementById('themeSelect').value;
    if (!theme) {
        showError('Please select a theme');
        return;
    }
    
    // Reset UI
    loading.style.display = 'block';
    error.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    // Update loading details
    const loadingDetails = document.getElementById('loadingDetails');
    loadingDetails.textContent = 'Analyzing your image...';
    
    try {
        const formData = new FormData();
        formData.append('image', currentImageBlob, 'selfie.jpg');
        formData.append('theme', theme);
        
        loadingDetails.textContent = 'Generating stylized image...';
        
        const response = await fetch('/transform', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Transformation failed');
        }
        
        const data = await response.json();
        
        // Display results
        displayResults(data, currentImageData, theme);
        
    } catch (err) {
        showError(err.message);
    } finally {
        loading.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Transform Image';
    }
});

function displayResults(data, originalImageData, theme) {
    // Show results view, hide form view
    formView.style.display = 'none';
    resultsView.style.display = 'block';
    
    // Display original image
    const originalContainer = document.getElementById('originalImageContainer');
    originalContainer.innerHTML = `<img src="${originalImageData}" alt="Original">`;
    
    // Display stylized image
    const stylizedContainer = document.getElementById('stylizedImageContainer');
    stylizedContainer.innerHTML = `<img src="data:image/png;base64,${data.stylized_image}" alt="Stylized">`;
    
    // Display info
    document.getElementById('resultTheme').textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
    document.getElementById('processingTime').textContent = `${data.processing_time_seconds}s`;
    document.getElementById('detectedFeatures').textContent = data.features || 'N/A';
    
    // Store data for download/share
    window.currentResult = data;
}

function showError(message) {
    document.getElementById('errorContent').textContent = message;
    error.style.display = 'block';
}

// Download button
downloadBtn.addEventListener('click', () => {
    if (!window.currentResult) return;
    
    const imageData = window.currentResult.stylized_image;
    const blob = base64ToBlob(imageData, 'image/png');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `stylized-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Share button (creates a shareable link - would need backend support)
shareBtn.addEventListener('click', () => {
    if (!window.currentResult) return;
    
    // For now, copy image to clipboard
    const imageData = window.currentResult.stylized_image;
    const blob = base64ToBlob(imageData, 'image/png');
    
    if (navigator.clipboard && navigator.clipboard.write) {
        navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob })
        ]).then(() => {
            alert('Image copied to clipboard!');
        }).catch(() => {
            alert('Could not copy to clipboard. Use download instead.');
        });
    } else {
        alert('Clipboard API not available. Use download instead.');
    }
});

// Start over button
startOverBtn.addEventListener('click', () => {
    form.reset();
    currentImageBlob = null;
    currentImageData = null;
    previewImage.style.display = 'none';
    noImageMessage.style.display = 'block';
    clearImageBtn.style.display = 'none';
    formView.style.display = 'block';
    resultsView.style.display = 'none';
    error.style.display = 'none';
    window.currentResult = null;
    updateSubmitButton();
    
    // Stop camera if running
    if (stream) {
        stopCameraBtn.click();
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// Helper function
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}
