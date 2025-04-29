document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const fileInput = document.getElementById('file-input');
    const textInput = document.getElementById('text-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsContainer = document.getElementById('results-container');
    const loadingSpinner = document.getElementById('loading-spinner');
    const alertContainer = document.getElementById('alert-container');
    const dropZone = document.getElementById('drop-zone');
    const resultsTableBody = document.getElementById('results-table-body');
    const reportTextarea = document.getElementById('report-textarea');
    const copyReportBtn = document.getElementById('copy-report-btn');
    const statsContainer = document.getElementById('stats-container');
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add drag and drop functionality
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('active');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('active');
            }, false);
        });
        
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            fileInput.files = dt.files;
            const fileName = fileInput.files[0]?.name || 'No file selected';
            document.getElementById('file-name').textContent = fileName;
        }, false);
    }
    
    // File input change handler
    fileInput.addEventListener('change', function() {
        const fileName = this.files[0]?.name || 'No file selected';
        document.getElementById('file-name').textContent = fileName;
    });
    
    // Analyze button click handler
    analyzeBtn.addEventListener('click', function() {
        // Check if either file or text input has data
        if (!fileInput.files[0] && !textInput.value.trim()) {
            showAlert('Please provide a file or enter WiFi data text', 'danger');
            return;
        }
        
        // Show loading spinner
        loadingSpinner.classList.remove('d-none');
        
        // Clear previous results
        clearResults();
        
        // Create form data
        const formData = new FormData();
        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }
        if (textInput.value.trim()) {
            formData.append('text_input', textInput.value.trim());
        }
        
        // Send request to server
        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'An error occurred during the analysis');
                });
            }
            return response.json();
        })
        .then(data => {
            displayResults(data);
        })
        .catch(error => {
            showAlert(error.message, 'danger');
        })
        .finally(() => {
            loadingSpinner.classList.add('d-none');
        });
    });
    
    // Function to clear previous results
    function clearResults() {
        resultsTableBody.innerHTML = '';
        reportTextarea.value = '';
        alertContainer.innerHTML = '';
        statsContainer.innerHTML = '';
    }
    
    // Function to show alerts
    function showAlert(message, type) {
        alertContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
    
    // Function to display results
    function displayResults(data) {
        if (!data.results || data.results.length === 0) {
            showAlert('No WiFi networks found in the provided data', 'warning');
            return;
        }
        
        // Show results container
        resultsContainer.classList.remove('d-none');
        
        // Display stats
        statsContainer.innerHTML = `
            <span class="badge bg-primary stat-badge">Total Networks: ${data.total}</span>
            <span class="badge bg-danger stat-badge">Flagged Networks: ${data.flagged}</span>
        `;
        
        // Generate table rows and report text
        let reportText = '';
        
        data.results.forEach(result => {
            // Add to table
            const row = document.createElement('tr');
            if (result.flagged) {
                row.classList.add('flagged-row');
            }
            
            row.innerHTML = `
                <td>${escapeHtml(result.ssid)}</td>
                <td class="format-column">${escapeHtml(result.bssid)}</td>
                <td class="format-column">----</td>
                <td>${escapeHtml(result.vendor)}</td>
            `;
            
            resultsTableBody.appendChild(row);
            
            // Add to report text
            reportText += `${result.ssid} ${result.bssid} ---- ${result.vendor}\n`;
        });
        
        // Set report text
        reportTextarea.value = reportText;
    }
    
    // Copy report button
    if (copyReportBtn) {
        copyReportBtn.addEventListener('click', function() {
            reportTextarea.select();
            document.execCommand('copy');
            
            // Show feedback
            const originalText = copyReportBtn.textContent;
            copyReportBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyReportBtn.textContent = originalText;
            }, 2000);
        });
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    // Sample data button (for demonstration)
    const sampleBtn = document.getElementById('sample-btn');
    if (sampleBtn) {
        sampleBtn.addEventListener('click', function() {
            textInput.value = `Company WiFi 00:11:22:33:44:55
Guest Network 66:77:88:99:aa:bb
Conference Room aa:bb:cc:dd:ee:ff
SSID: IT Department, BSSID: 11:22:33:44:55:66
Free WiFi 12:34:56:78:90:ab
ICPS 74:83:c2:2d:1d:b1
Visitor 24:a0:74:1e:9f:ac`;
        });
    }
});
