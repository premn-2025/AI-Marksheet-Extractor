class MarksheetExtractor {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.currentResults = null;
    }

    initializeElements() {
        // Single file upload
        this.fileInput = document.getElementById('fileInput');
        this.uploadArea = document.getElementById('uploadArea');
        this.extractBtn = document.getElementById('extractBtn');

        // Batch upload
        this.batchFileInput = document.getElementById('batchFileInput');
        this.batchUploadArea = document.getElementById('batchUploadArea');
        this.batchExtractBtn = document.getElementById('batchExtractBtn');

        // Sections
        this.loadingSection = document.getElementById('loadingSection');
        this.resultsSection = document.getElementById('resultsSection');

        // Results
        this.summaryCards = document.getElementById('summaryCards');
        this.formattedResults = document.getElementById('formattedResults');
        this.jsonOutput = document.getElementById('jsonOutput');

        // Actions
        this.downloadBtn = document.getElementById('downloadBtn');
        this.newExtractionBtn = document.getElementById('newExtractionBtn');
    }

    attachEventListeners() {
        // Single file upload
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        this.extractBtn.addEventListener('click', this.extractSingle.bind(this));

        // Batch upload
        this.batchUploadArea.addEventListener('click', () => this.batchFileInput.click());
        this.batchUploadArea.addEventListener('dragover', this.handleBatchDragOver.bind(this));
        this.batchUploadArea.addEventListener('dragleave', this.handleBatchDragLeave.bind(this));
        this.batchUploadArea.addEventListener('drop', this.handleBatchDrop.bind(this));
        this.batchFileInput.addEventListener('change', this.handleBatchFileSelect.bind(this));
        this.batchExtractBtn.addEventListener('click', this.extractBatch.bind(this));

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', this.switchTab.bind(this));
        });

        // Actions
        this.downloadBtn.addEventListener('click', this.downloadResults.bind(this));
        this.newExtractionBtn.addEventListener('click', this.resetInterface.bind(this));
    }

    // Drag and Drop Handlers
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.fileInput.files = files;
            this.handleFileSelect();
        }
    }

    handleBatchDragOver(e) {
        e.preventDefault();
        this.batchUploadArea.classList.add('dragover');
    }

    handleBatchDragLeave(e) {
        e.preventDefault();
        this.batchUploadArea.classList.remove('dragover');
    }

    handleBatchDrop(e) {
        e.preventDefault();
        this.batchUploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.batchFileInput.files = files;
            this.handleBatchFileSelect();
        }
    }

    // File Selection Handlers
    handleFileSelect() {
        const file = this.fileInput.files[0];
        if (file) {
            if (this.validateFile(file)) {
                this.uploadArea.classList.add('file-selected');
                this.uploadArea.querySelector('p').innerHTML = `Selected: <strong>${file.name}</strong>`;
                this.extractBtn.disabled = false;
            }
        }
    }

    handleBatchFileSelect() {
        const files = this.batchFileInput.files;
        if (files.length > 0) {
            if (this.validateBatchFiles(files)) {
                this.batchUploadArea.classList.add('file-selected');
                this.batchUploadArea.querySelector('p').innerHTML = `Selected: <strong>${files.length} files</strong>`;
                this.batchExtractBtn.disabled = false;
            }
        }
    }

    validateFile(file) {
        // FIX: Add WebP support
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'application/pdf'];
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!validTypes.includes(file.type)) {
            this.showError('Invalid file type. Please upload JPG, PNG, WebP, or PDF files.');
            return false;
        }

        if (file.size > maxSize) {
            this.showError('File too large. Maximum size is 10MB.');
            return false;
        }

        return true;
    }

    validateBatchFiles(files) {
        if (files.length > 10) {
            this.showError('Too many files. Maximum 10 files allowed per batch.');
            return false;
        }

        for (let i = 0; i < files.length; i++) {
            if (!this.validateFile(files[i])) {
                return false;
            }
        }

        return true;
    }

    showError(message) {
        // Show error on both upload areas
        const areas = [this.uploadArea, this.batchUploadArea];
        
        areas.forEach(area => {
            area.classList.add('upload-error');
            
            // Remove existing error message
            const existingError = area.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }

            // Add new error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = message;
            area.appendChild(errorDiv);

            setTimeout(() => {
                area.classList.remove('upload-error');
                errorDiv.remove();
            }, 5000);
        });
    }

    // Extraction Methods
    async extractSingle() {
        const file = this.fileInput.files[0];
        if (!file) return;

        this.showLoading();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/extract', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.currentResults = result;
            this.displayResults(result);
        } catch (error) {
            this.showError(`Extraction failed: ${error.message}`);
            this.hideLoading();
        }
    }

    async extractBatch() {
        const files = this.batchFileInput.files;
        if (files.length === 0) return;

        this.showLoading();

        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }

        try {
            const response = await fetch('/extract/batch', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const results = await response.json();
            this.currentResults = results;
            this.displayBatchResults(results);
        } catch (error) {
            this.showError(`Batch extraction failed: ${error.message}`);
            this.hideLoading();
        }
    }

    showLoading() {
        this.loadingSection.style.display = 'block';
        this.resultsSection.style.display = 'none';
        // Scroll to loading section
        this.loadingSection.scrollIntoView({ behavior: 'smooth' });
    }

    hideLoading() {
        this.loadingSection.style.display = 'none';
    }

    // Results Display
    displayResults(result) {
        this.hideLoading();
        this.resultsSection.style.display = 'block';

        // Create summary cards
        this.createSummaryCards(result);
        
        // Display formatted results
        this.displayFormattedResults(result);
        
        // Display JSON
        this.jsonOutput.textContent = JSON.stringify(result, null, 2);

        // Scroll to results
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    displayBatchResults(results) {
        this.hideLoading();
        this.resultsSection.style.display = 'block';

        // For batch results, show summary of all files
        this.createBatchSummaryCards(results);
        
        // Display all results
        this.displayFormattedBatchResults(results);
        
        // Display JSON
        this.jsonOutput.textContent = JSON.stringify(results, null, 2);

        // Scroll to results
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    createSummaryCards(result) {
        const data = result.data || {};
        const avgConfidence = this.calculateAverageConfidence(data);
        
        this.summaryCards.innerHTML = `
            <div class="summary-card ${this.getConfidenceClass(avgConfidence)}">
                <div class="metric">${Math.round(avgConfidence * 100)}%</div>
                <div class="label">Avg Confidence</div>
            </div>
            <div class="summary-card">
                <div class="metric">${data.subjects?.length || 0}</div>
                <div class="label">Subjects Found</div>
            </div>
            <div class="summary-card">
                <div class="metric">${this.getNestedValue(data, 'overall_result.total_marks') || 'N/A'}</div>
                <div class="label">Total Marks</div>
            </div>
            <div class="summary-card">
                <div class="metric">${this.getNestedValue(data, 'overall_result.percentage') || this.getNestedValue(data, 'overall_result.grade') || 'N/A'}</div>
                <div class="label">Result</div>
            </div>
        `;
    }

    createBatchSummaryCards(results) {
        const totalFiles = results.results?.length || 0;
        const successfulExtractions = results.results?.filter(r => r.success).length || 0;
        
        this.summaryCards.innerHTML = `
            <div class="summary-card">
                <div class="metric">${totalFiles}</div>
                <div class="label">Total Files</div>
            </div>
            <div class="summary-card ${successfulExtractions === totalFiles ? 'high-confidence' : 'medium-confidence'}">
                <div class="metric">${successfulExtractions}</div>
                <div class="label">Successful</div>
            </div>
            <div class="summary-card">
                <div class="metric">${totalFiles - successfulExtractions}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="metric">${totalFiles > 0 ? Math.round((successfulExtractions / totalFiles) * 100) : 0}%</div>
                <div class="label">Success Rate</div>
            </div>
        `;
    }

    displayFormattedResults(result) {
        const data = result.data || {};
        
        let html = '';
        
        // Candidate Information
        if (data.candidate_info) {
            html += this.createInfoSection('Candidate Information', data.candidate_info);
        }
        
        // Subjects
        if (data.subjects && data.subjects.length > 0) {
            html += this.createSubjectsSection(data.subjects);
        }
        
        // Overall Result
        if (data.overall_result) {
            html += this.createInfoSection('Overall Result', data.overall_result);
        }
        
        // Additional Information
        if (data.additional_info) {
            html += this.createInfoSection('Additional Information', data.additional_info);
        }

        // If no data found
        if (!html) {
            html = '<div class="result-section"><h3>No data extracted</h3><p>The AI could not extract structured data from this marksheet.</p></div>';
        }
        
        this.formattedResults.innerHTML = html;
    }

    displayFormattedBatchResults(results) {
        let html = '';
        
        if (!results.results || results.results.length === 0) {
            html = '<div class="result-section"><h3>No results</h3><p>No files were processed.</p></div>';
        } else {
            results.results.forEach((result, index) => {
                const filename = result.filename || `File ${index + 1}`;
                
                if (result.success) {
                    html += `<div class="result-section">
                        <h3><i class="fas fa-file"></i> ${filename}</h3>
                        ${this.createFormattedResultContent(result.data || {})}
                    </div>`;
                } else {
                    html += `<div class="result-section">
                        <h3 style="color: var(--danger-color);"><i class="fas fa-exclamation-triangle"></i> ${filename} - Failed</h3>
                        <p style="color: var(--danger-color);">${result.error || 'Unknown error occurred'}</p>
                    </div>`;
                }
            });
        }
        
        this.formattedResults.innerHTML = html;
    }

    createFormattedResultContent(data) {
        let html = '';
        
        if (data.candidate_info) {
            html += this.createInfoGrid(data.candidate_info);
        }
        
        if (data.subjects && data.subjects.length > 0) {
            html += this.createSubjectsTable(data.subjects);
        }

        if (!html) {
            html = '<p style="color: var(--text-secondary);">No structured data extracted from this file.</p>';
        }
        
        return html;
    }

    createInfoSection(title, info) {
        return `
            <div class="result-section">
                <h3>${title}</h3>
                ${this.createInfoGrid(info)}
            </div>
        `;
    }

    createInfoGrid(info) {
        let html = '<div class="info-grid">';
        let hasData = false;
        
        for (const [key, value] of Object.entries(info)) {
            if (typeof value === 'object' && value !== null && value.value !== undefined) {
                const confidence = value.confidence || 0;
                const displayValue = value.value || 'N/A';
                html += `
                    <div class="info-item">
                        <span class="info-label">${this.formatLabel(key)}:</span>
                        <span class="info-value">
                            ${displayValue}
                            <span class="confidence-badge ${this.getConfidenceClass(confidence)}">
                                ${Math.round(confidence * 100)}%
                            </span>
                        </span>
                    </div>
                `;
                hasData = true;
            } else if (value && typeof value !== 'object') {
                html += `
                    <div class="info-item">
                        <span class="info-label">${this.formatLabel(key)}:</span>
                        <span class="info-value">${value}</span>
                    </div>
                `;
                hasData = true;
            }
        }
        
        html += '</div>';
        
        if (!hasData) {
            return '<p style="color: var(--text-secondary);">No information available</p>';
        }
        
        return html;
    }

    createSubjectsSection(subjects) {
        return `
            <div class="result-section">
                <h3>Subjects and Marks</h3>
                ${this.createSubjectsTable(subjects)}
            </div>
        `;
    }

    createSubjectsTable(subjects) {
        let html = `
            <table class="subjects-table">
                <thead>
                    <tr>
                        <th>Subject</th>
                        <th>Obtained</th>
                        <th>Maximum</th>
                        <th>Grade</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        subjects.forEach(subject => {
            const avgConfidence = this.calculateSubjectConfidence(subject);
            html += `
                <tr>
                    <td>${this.getValue(subject.subject)}</td>
                    <td>${this.getValue(subject.obtained_marks)}</td>
                    <td>${this.getValue(subject.max_marks)}</td>
                    <td>${this.getValue(subject.grade)}</td>
                    <td>
                        <span class="confidence-badge ${this.getConfidenceClass(avgConfidence)}">
                            ${Math.round(avgConfidence * 100)}%
                        </span>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        return html;
    }

    getValue(field) {
        if (typeof field === 'object' && field !== null && field.value !== undefined) {
            return field.value || 'N/A';
        }
        return field || 'N/A';
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            if (current && typeof current === 'object') {
                const value = current[key];
                if (typeof value === 'object' && value !== null && value.value !== undefined) {
                    return value.value;
                }
                return value;
            }
            return undefined;
        }, obj);
    }

    calculateSubjectConfidence(subject) {
        const fields = ['subject', 'obtained_marks', 'max_marks', 'grade'];
        let totalConfidence = 0;
        let count = 0;
        
        fields.forEach(field => {
            if (subject[field] && typeof subject[field] === 'object' && subject[field].confidence !== undefined) {
                totalConfidence += subject[field].confidence;
                count++;
            }
        });
        
        return count > 0 ? totalConfidence / count : 0;
    }

    calculateAverageConfidence(data) {
        let allConfidences = [];
        
        // Extract confidences from all fields
        const extractConfidences = (obj) => {
            if (!obj || typeof obj !== 'object') return;
            
            for (const [key, value] of Object.entries(obj)) {
                if (typeof value === 'object' && value !== null) {
                    if (value.confidence !== undefined) {
                        allConfidences.push(value.confidence);
                    } else if (Array.isArray(value)) {
                        value.forEach(item => extractConfidences(item));
                    } else {
                        extractConfidences(value);
                    }
                }
            }
        };
        
        extractConfidences(data);
        
        return allConfidences.length > 0 
            ? allConfidences.reduce((sum, conf) => sum + conf, 0) / allConfidences.length 
            : 0;
    }

    getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'confidence-high';
        if (confidence >= 0.6) return 'confidence-medium';
        return 'confidence-low';
    }

    formatLabel(key) {
        return key.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    // Tab Management
    switchTab(event) {
        const tabName = event.target.getAttribute('data-tab');
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        
        // Update tab panes
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        const targetTab = document.getElementById(tabName + 'Tab');
        if (targetTab) {
            targetTab.classList.add('active');
        }
    }

    // Utility Functions
    downloadResults() {
        if (!this.currentResults) return;
        
        const dataStr = JSON.stringify(this.currentResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        
        // Create filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        link.download = `marksheet-extraction-${timestamp.split('T')[0]}.json`;
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(link.href);
    }

    resetInterface() {
        // Reset file inputs
        this.fileInput.value = '';
        this.batchFileInput.value = '';
        
        // Reset upload areas
        this.uploadArea.classList.remove('file-selected', 'upload-error');
        this.batchUploadArea.classList.remove('file-selected', 'upload-error');
        
        // Reset upload area text
        this.uploadArea.querySelector('p').innerHTML = 'Drag & drop your marksheet here or <span class="browse-link">browse</span>';
        this.batchUploadArea.querySelector('p').innerHTML = 'Upload multiple marksheets';
        
        // Remove any error messages
        this.uploadArea.querySelectorAll('.error-message').forEach(el => el.remove());
        this.batchUploadArea.querySelectorAll('.error-message').forEach(el => el.remove());
        
        // Disable buttons
        this.extractBtn.disabled = true;
        this.batchExtractBtn.disabled = true;
        
        // Hide sections
        this.loadingSection.style.display = 'none';
        this.resultsSection.style.display = 'none';
        
        // Clear results
        this.currentResults = null;
        this.summaryCards.innerHTML = '';
        this.formattedResults.innerHTML = '';
        this.jsonOutput.textContent = '';
        
        // Reset to formatted tab
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        document.querySelector('.tab-btn[data-tab="formatted"]').classList.add('active');
        document.getElementById('formattedTab').classList.add('active');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new MarksheetExtractor();
});
