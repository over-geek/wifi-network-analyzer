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
    
    // Advanced analysis elements
    const orgSsidsInput = document.getElementById('org-ssids');
    const updateAnalysisBtn = document.getElementById('update-analysis-btn');
    const unknownVendorsTextarea = document.getElementById('unknown-vendors-textarea');
    const knownVendorsTextarea = document.getElementById('known-vendors-textarea');
    const copyUnknownBtn = document.getElementById('copy-unknown-btn');
    const copyKnownBtn = document.getElementById('copy-known-btn');
    
    // Store analysis results globally for advanced analysis
    let analysisResults = [];
    
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

    document.querySelectorAll('#inputTabs .nav-link').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (e) {
            // Clear the other input when switching tabs
            if (e.target.id === 'file-tab') {
                textInput.value = '';
            } else if (e.target.id === 'text-tab') {
                // Clear file input (this requires a workaround since file inputs can't be directly cleared)
                fileInput.value = '';
                document.getElementById('file-name').textContent = 'No file selected';
            }
        });
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
        
        // Store results for advanced analysis
        analysisResults = data.results.map(result => {
            // Clean SSID of any True/False prefixes
            let cleanSsid = result.ssid.replace(/^(True|False)\s+/, '');
            return {
                ...result,
                ssid: cleanSsid
            };
        });
        
        // Show results container
        resultsContainer.classList.remove('d-none');
        
        // Display stats
        statsContainer.innerHTML = `
            <span class="badge bg-primary stat-badge">Total Networks: ${data.total}</span>
            <span class="badge bg-danger stat-badge">Flagged Networks: ${data.flagged}</span>
        `;
        
        // Generate table rows and report text
        let reportText = '';
        
        analysisResults.forEach(result => {
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
        
        // Also update the advanced analysis if we have data
        // Check if advanced analysis elements exist before updating
        if (document.getElementById('advanced-tab-pane')) {
            updateAdvancedAnalysis();
        }
    }
    
    // Function to check if a network belongs to the organization
    function isOrganizationNetwork(ssid, orgSsids) {
        if (!orgSsids || !ssid) return false;
        
        // Clean up and normalize organization SSIDs
        const normalizedOrgSsids = orgSsids
            .split(',')
            .map(s => s.trim().toLowerCase())
            .filter(s => s.length > 0);
        
        // Check if the network SSID matches any organization SSID
        return normalizedOrgSsids.some(orgSsid => 
            ssid.toLowerCase().includes(orgSsid) || 
            orgSsid.includes(ssid.toLowerCase())
        );
    }
    
    // Function to update the advanced analysis tab
    function updateAdvancedAnalysis() {
        if (!analysisResults || analysisResults.length === 0) return;
        
        // Check if all required elements exist
        if (!document.getElementById('org-ssids') || 
            !document.getElementById('unknown-vendors-textarea') || 
            !document.getElementById('known-vendors-textarea')) {
            console.error('Advanced analysis elements not found');
            return;
        }
        
        // Get organization SSIDs
        const orgSsids = orgSsidsInput.value;
        
        // Filter networks
        const unknownVendorNetworks = analysisResults.filter(network => 
            !isOrganizationNetwork(network.ssid, orgSsids) && 
            (!network.vendor || network.vendor.includes('no match'))
        );
        
        const knownVendorNetworks = analysisResults.filter(network => 
            !isOrganizationNetwork(network.ssid, orgSsids) && 
            network.vendor && !network.vendor.includes('no match')
        );
        
        // Format for unknown vendor networks (excluding organization networks)
        if (unknownVendorNetworks.length > 0) {
            // Format as a quoted list with commas between items
            const formattedUnknown = unknownVendorNetworks
                .map(network => `"${network.ssid}"`)
                .join(', ');
                
            unknownVendorsTextarea.value = formattedUnknown;
        } else {
            unknownVendorsTextarea.value = 'No unknown vendor networks found (excluding organization networks)';
        }
        
        // Format for known vendor networks (excluding organization networks)
        if (knownVendorNetworks.length > 0) {
            // Format SSIDs list
            const formattedSsids = knownVendorNetworks
                .map(network => `"${network.ssid}"`)
                .join(', ');
                
            // Format vendors list
            const formattedVendors = knownVendorNetworks
                .map(network => `"${network.vendor}"`)
                .join(', ');
                
            knownVendorsTextarea.value = formattedSsids + '\n\n----------------------------------------------\n\n' + formattedVendors;
        } else {
            knownVendorsTextarea.value = 'No known vendor networks found (excluding organization networks)';
        }
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
    
    // Update analysis button event listener
    if (updateAnalysisBtn) {
        updateAnalysisBtn.addEventListener('click', function() {
            updateAdvancedAnalysis();
        });
    }
    
    // Copy unknown vendors button
    if (copyUnknownBtn) {
        copyUnknownBtn.addEventListener('click', function() {
            unknownVendorsTextarea.select();
            document.execCommand('copy');
            
            // Show feedback
            const originalText = copyUnknownBtn.textContent;
            copyUnknownBtn.innerHTML = '<i class="bi bi-clipboard-check"></i> Copied!';
            setTimeout(() => {
                copyUnknownBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
            }, 2000);
        });
    }
    
    // Copy known vendors button
    if (copyKnownBtn) {
        copyKnownBtn.addEventListener('click', function() {
            knownVendorsTextarea.select();
            document.execCommand('copy');
            
            // Show feedback
            const originalText = copyKnownBtn.textContent;
            copyKnownBtn.innerHTML = '<i class="bi bi-clipboard-check"></i> Copied!';
            setTimeout(() => {
                copyKnownBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
            }, 2000);
        });
    }
});
