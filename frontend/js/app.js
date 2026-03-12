// ===== Auth Check & Logout Logic =====
// Validate session on page load using JWT token
const API_BASE = window.location.origin;
const token = localStorage.getItem('civic_token');

if (!token) {
    window.location.href = 'login.html';
} else {
    // Verify token with server
    fetch(API_BASE + '/api/me', {
        headers: { 'Authorization': 'Bearer ' + token }
    }).then(response => {
        if (!response.ok) {
            // Token invalid or expired — clear and redirect
            localStorage.removeItem('civic_token');
            localStorage.removeItem('civic_logged_in');
            localStorage.removeItem('civic_current_user');
            window.location.href = 'login.html';
        } else {
            return response.json();
        }
    }).then(user => {
        if (user) {
            // Update stored user data with fresh server data
            localStorage.setItem('civic_current_user', JSON.stringify(user));
        }
    }).catch(() => {
        // Network error — redirect to login
        localStorage.removeItem('civic_token');
        localStorage.removeItem('civic_logged_in');
        localStorage.removeItem('civic_current_user');
        window.location.href = 'login.html';
    });
}

function logoutUser() {
    localStorage.removeItem('civic_token');
    localStorage.removeItem('civic_logged_in');
    localStorage.removeItem('civic_current_user');
    window.location.href = 'login.html';
}

function toggleUserProfile() {
    const menu = document.getElementById('user-profile-menu');
    const isVisible = menu.style.display === 'block';

    if (!isVisible) {
        // Populate data from stored user info
        const userStr = localStorage.getItem('civic_current_user');
        if (userStr) {
            const user = JSON.parse(userStr);
            document.getElementById('profile-name').innerText = user.name || 'N/A';
            document.getElementById('profile-email').innerText = user.email || 'N/A';
            document.getElementById('profile-phone').innerText = user.phone || 'N/A';
        }
        menu.style.display = 'block';
    } else {
        menu.style.display = 'none';
    }
}

// Close dropdown if clicked outside
document.addEventListener('click', function (event) {
    const dropdown = document.querySelector('.user-profile-dropdown');
    const menu = document.getElementById('user-profile-menu');
    if (dropdown && menu && !dropdown.contains(event.target)) {
        menu.style.display = 'none';
    }
});

// ===== Search and Chat logic =====
const searchInput = document.getElementById('ai-search-input');

function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;
    simulateAIResponse(query);
}

// Allow Enter key to search
searchInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

function executeQuickQuery(query) {
    searchInput.value = query;
    handleSearch();
}

// ===== Modal Logic =====
const modal = document.getElementById('ai-response-modal');
const modalBody = document.getElementById('ai-response-body');

function openModal() {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

window.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// ===== Notice Upload Logic =====
function triggerNoticeUpload() {
    document.getElementById('notice-upload-input').click();
}

async function handleNoticeUpload(input) {
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const originalBody = modalBody.innerHTML;

    // Show loading state
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Analyzing Government Notice...</h3>
            <p>Extracting text and identifying the department. Please wait.</p>
        </div>
    `;
    openModal();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(API_BASE + '/api/explain_notice', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token'),
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderAIResponse(data, "Notice Explanation Result");

    } catch (error) {
        console.error("Error explaining notice:", error);
        modalBody.innerHTML = `
            <div class="ai-reasoning text-center" style="text-align:center; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 3rem; margin-bottom: 20px;"></i>
                <h3>Extraction Failed</h3>
                <p>Could not process the uploaded notice. Ensure the file is a valid PDF or Image and under 10MB.</p>
            </div>
        `;
    } finally {
        input.value = ''; // Clear input
    }
}

// ===== AI Response =====
async function simulateAIResponse(query) {
    // Show loading state
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Analyzing query...</h3>
            <p>Please wait while CivicAssist retrieves the information securely.</p>
        </div>
    `;
    openModal();

    try {
        const response = await fetch(API_BASE + '/api/ask_tax_question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token'),
            },
            body: JSON.stringify({ question: query })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderAIResponse(data, "AI Analysis Result");

    } catch (error) {
        console.error("Error communicating with AI:", error);
        modalBody.innerHTML = `
            <div class="ai-reasoning text-center" style="text-align:center; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 3rem; margin-bottom: 20px;"></i>
                <h3>Connection Error</h3>
                <p>Could not connect to the CivicAssist AI backend. Ensure the server is running on port 8000.</p>
            </div>
        `;
    }
}

function renderAIResponse(data, title) {
    let stepsHtml = '';
    if (data.steps && data.steps.length > 0) {
        stepsHtml = `
            <div class="ai-next-steps" style="margin-top: 20px;">
                <h4><i class="fa-solid fa-shoe-prints"></i> Recommended Next Steps</h4>
                <div class="steps-container" style="padding-left: 20px; line-height: 1.6;">
                    <ul style="list-style-type: decimal;">
                        ${data.steps.map(step => `<li>${step}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }

    let deadlineHtml = '';
    if (data.deadline) {
        deadlineHtml = `
            <div class="ai-alert" style="background: #fff5f5; border: 1px solid #feb2b2; padding: 10px; border-radius: 6px; margin-top: 15px; color: #c53030;">
                <i class="fa-solid fa-clock"></i> <strong>Deadline Found:</strong> ${data.deadline}
            </div>
        `;
    }

    let sourcesHtml = '';
    if (data.sources && data.sources.length > 0) {
        sourcesHtml = `
            <div class="ai-sources" style="margin-top: 15px; font-size: 0.8rem; color: #718096; border-top: 1px solid #edf2f7; padding-top: 10px;">
                <i class="fa-solid fa-book"></i> <strong>Verified Sources:</strong> ${data.sources.join(', ')}
            </div>
        `;
    }

    modalBody.innerHTML = `
        <div class="ai-reasoning">
            <h4 style="color: var(--accent-purple); display: flex; align-items: center; gap: 8px;">
                <i class="fa-solid fa-robot"></i> ${title}
            </h4>
            <div style="margin: 10px 0; font-size: 0.95rem; line-height: 1.5; color: #2d3748;">
                <p><strong>Department:</strong> ${data.department?.toUpperCase() || 'General'}</p>
                ${data.notice_type ? `<p><strong>Notice Type:</strong> ${data.notice_type}</p>` : ''}
            </div>
            <p style="background: #f7fafc; padding: 15px; border-radius: 8px; border-left: 4px solid var(--accent-purple); margin-bottom: 20px;">
                ${data.explanation}
            </p>
        </div>
        ${deadlineHtml}
        ${stepsHtml}
        ${sourcesHtml}
    `;
}

// ===== Service Card Logic =====
function openServiceModal(serviceName) {
    const templateId = `${serviceName.toLowerCase()}-features-template`;
    const template = document.getElementById(templateId);

    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    } else {
        modalBody.innerHTML = `
            <div class="ai-reasoning text-center" style="text-align:center;">
                <i class="fa-solid fa-robot" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
                <h3>${serviceName} Assistant</h3>
                <p style="margin-top: 15px;">What specifically do you need help with regarding ${serviceName}?</p>
                <div class="search-box glass-panel" style="margin-top: 20px; border: 1px solid var(--border-color);">
                    <input type="text" placeholder="Ask a question..." autocomplete="off">
                    <button class="btn btn-gradient search-action" style="padding: 8px 16px; background-color: var(--primary-red); color: white;">Ask AI</button>
                </div>
            </div>
        `;
    }

    openModal();
}

// ===== Document Manager Logic =====
async function checkDocumentStatus() {
    try {
        const response = await fetch(API_BASE + '/api/user_documents', {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        if (response.ok) {
            const data = await response.json();
            const types = data.uploaded_types || [];
            
            updateDocStatusUI('aadhaar', types.includes('aadhaar'));
            updateDocStatusUI('pan', types.includes('pan'));
        }
    } catch (e) {
        console.error("Failed to fetch doc status", e);
    }
}

function updateDocStatusUI(type, isUploaded) {
    const statusEl = document.getElementById(`status-${type}`);
    const actionEl = document.getElementById(`action-${type}`);
    if (!statusEl || !actionEl) return;

    if (isUploaded) {
        statusEl.innerHTML = '<i class="fa-solid fa-circle-check"></i> Uploaded ✓';
        statusEl.classList.add('uploaded');
        
        // Match Image 2: View, Download, Replace (Verify added for functionality)
        actionEl.innerHTML = `
            <div class="doc-actions-row">
                <button class="btn-doc-action" onclick="viewDocument('${type}')"><i class="fa-regular fa-eye"></i> View</button>
                <button class="btn-doc-action" onclick="downloadDocument('${type}')"><i class="fa-solid fa-download"></i> Download</button>
                <label class="btn-doc-action btn-replace">
                    <i class="fa-solid fa-arrows-rotate"></i> Replace
                    <input type="file" onchange="uploadDocument('${type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display:none;">
                </label>
            </div>
        `;
    } else {
        statusEl.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Not Uploaded';
        statusEl.classList.remove('uploaded');
        
        // Show primary Upload button
        actionEl.innerHTML = `
            <label class="btn-upload">
                <i class="fa-solid fa-upload"></i> Upload
                <input type="file" onchange="uploadDocument('${type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display:none;">
            </label>
        `;
    }
}

async function viewDocument(type) {
    const token = localStorage.getItem('civic_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/view_document/${type}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        } else if (response.status === 401) {
            alert("Unauthorized access – please login again");
            logoutUser();
        } else {
            const err = await response.json();
            alert("Error viewing document: " + (err.detail || "Unknown error"));
        }
    } catch (e) {
        console.error("View error:", e);
        alert("Failed to connect to server for viewing.");
    }
}

async function downloadDocument(type) {
    const token = localStorage.getItem('civic_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/download_document/${type}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const blob = await response.blob();
            // Create a temporary link to download with the correct extension
            const contentDisp = response.headers.get('Content-Disposition');
            let filename = `${type}_document.pdf`;
            if (contentDisp && contentDisp.includes('filename=')) {
                // Better filename extraction
                const parts = contentDisp.split(';');
                for (let part of parts) {
                    if (part.trim().startsWith('filename=')) {
                        filename = part.split('=')[1].trim().replace(/"/g, '');
                    }
                }
            }
            
            const url = URL.createObjectURL(new Blob([blob], { type: response.headers.get('Content-Type') || 'application/octet-stream' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else if (response.status === 401) {
            alert("Unauthorized access – please login again");
            logoutUser();
        } else {
            const err = await response.json();
            alert("Error downloading document: " + (err.detail || "Unknown error"));
        }
    } catch (e) {
        console.error("Download error:", e);
        alert("Failed to connect to server for download.");
    }
}

async function verifyIntegrity(type) {
    const token = localStorage.getItem('civic_token');
    if (!token) return;

    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Verifying Document Integrity...</h3>
            <p>Comparing document hash with blockchain ledger.</p>
        </div>
    `;
    openModal();

    try {
        const response = await fetch(`${API_BASE}/api/verify_integrity/${type}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (response.ok) {
            const data = await response.json();
            
            if (data.authentic) {
                modalBody.innerHTML = `
                    <div class="ai-reasoning text-center" style="text-align:center;">
                        <i class="fa-solid fa-circle-check" style="font-size: 4rem; color: #00b074; margin-bottom: 20px;"></i>
                        <h2 style="color: #00b074;">Document Authentic</h2>
                        <p>The document hash matches the value stored on the blockchain.</p>
                        <div style="text-align:left; background: #f8fafc; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 0.8rem;">
                            <p><strong>Stored Hash:</strong> ${data.stored_hash}</p>
                            <p><strong>Current Hash:</strong> ${data.current_hash}</p>
                            <p><strong>Verified At:</strong> ${new Date().toLocaleString()}</p>
                        </div>
                    </div>
                `;
            } else {
                modalBody.innerHTML = `
                    <div class="ai-reasoning text-center" style="text-align:center;">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 4rem; color: var(--primary-red); margin-bottom: 20px;"></i>
                        <h2 style="color: var(--primary-red);">Integrity Compromised</h2>
                        <p><strong>WARNING:</strong> The document hash does not match the blockchain record. This document may have been tampered with.</p>
                        <div style="text-align:left; background: #fff5f5; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 0.8rem; border: 1px solid #feb2b2;">
                            <p><strong>Stored Hash:</strong> ${data.stored_hash || 'Record Missing'}</p>
                            <p><strong>Current Hash:</strong> ${data.current_hash}</p>
                        </div>
                    </div>
                `;
            }
        } else {
            const err = await response.json();
            alert("Verification failed: " + (err.detail || "Unknown error"));
            closeModal();
        }
    } catch (e) {
        console.error("Verification error:", e);
        alert("Failed to connect to server for verification.");
        closeModal();
    }
}

async function uploadDocument(type, input) {
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const label = input.parentElement;
    const originalHTML = label.innerHTML;
    
    label.classList.add('loading');
    label.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Uploading...';

    const formData = new FormData();
    formData.append('doc_type', type);
    formData.append('file', file);

    try {
        const response = await fetch(API_BASE + '/api/upload_document', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            alert(`${type.toUpperCase()} uploaded successfully!`);
            checkDocumentStatus();
        } else {
            const err = await response.json();
            alert("Upload failed: " + (err.detail || "Unknown error"));
        }
    } catch (e) {
        alert("Server connection error during upload.");
    } finally {
        label.classList.remove('loading');
        label.innerHTML = originalHTML;
        input.value = ''; // clear input
    }
}

// --- EPFO PF Withdrawal Modes Logic ---

function showPFOptions() {
    const template = document.getElementById('pf-options-template');
    if (!template) return;
    
    // Clear and inject into modal body
    modalBody.innerHTML = '';
    modalBody.appendChild(template.content.cloneNode(true));
    openModal();
}

function revertToEPFOGrid() {
    const template = document.getElementById('epfo-features-template');
    if (!template) return;
    
    modalBody.innerHTML = '';
    modalBody.appendChild(template.content.cloneNode(true));
}

async function showPFGuidance() {
    const template = document.getElementById('pf-guidance-template');
    if (!template) return;
    
    modalBody.innerHTML = '';
    modalBody.appendChild(template.content.cloneNode(true));

    // Fetch identity info from backend
    try {
        const token = localStorage.getItem('civic_token');
        const response = await fetch(`${API_BASE}/api/epfo/user-info`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('pf-guidance-name').innerText = data.name;
            document.getElementById('pf-guidance-dob').innerText = data.dob;
        } else {
            document.getElementById('pf-guidance-name').innerText = "Error loading";
            document.getElementById('pf-guidance-dob').innerText = "Error loading";
        }
    } catch (e) {
        console.error("Guidance info error:", e);
    }
}

function showPFVerification() {
    const template = document.getElementById('pf-verification-template');
    if (!template) return;
    
    modalBody.innerHTML = '';
    modalBody.appendChild(template.content.cloneNode(true));

    // Set up upload zone click
    const zone = document.getElementById('passbook-upload-zone');
    const input = document.getElementById('passbook-input');
    zone.onclick = () => input.click();
}

async function verifyPassbook(input) {
    if (!input.files || !input.files[0]) return;
    
    const zone = document.getElementById('passbook-upload-zone');
    const resultContainer = document.getElementById('verification-result-container');
    const originalHTML = zone.innerHTML;
    
    zone.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><p>Scanning Passbook & Verifying...</p>';
    zone.style.pointerEvents = 'none';

    const formData = new FormData();
    formData.append('file', input.files[0]);

    try {
        const token = localStorage.getItem('civic_token');
        const response = await fetch(`${API_BASE}/api/epfo/verify-passbook`, {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            renderVerificationResults(data);
        } else {
            alert("Verification failed. Please try again with a clearer image.");
            zone.innerHTML = originalHTML;
            zone.style.pointerEvents = 'auto';
        }
    } catch (e) {
        console.error("Verification error:", e);
        alert("Server error during verification.");
        zone.innerHTML = originalHTML;
        zone.style.pointerEvents = 'auto';
    }
}

function renderVerificationResults(data) {
    const container = document.getElementById('verification-result-container');
    const zone = document.getElementById('passbook-upload-zone');
    zone.style.display = 'none';
    container.style.display = 'block';

    const statusClass = data.status === 'Verified' ? 'status-verified' : 'status-issues';
    const statusIcon = data.status === 'Verified' ? 'fa-circle-check' : 'fa-triangle-exclamation';

    let issuesHTML = '';
    if (data.detected_issues && data.detected_issues.length > 0) {
        issuesHTML = `
            <div class="issue-list">
                ${data.detected_issues.map(issue => `
                    <div class="issue-item"><i class="fa-solid fa-xmark"></i> ${issue}</div>
                `).join('')}
            </div>
        `;
    }

    container.innerHTML = `
        <div class="result-card">
            <div class="result-status ${statusClass}">
                <i class="fa-solid ${statusIcon}"></i>
                Status: ${data.status}
            </div>
            
            ${issuesHTML}

            <div class="fix-box">
                <div class="fix-title">Next Steps / Suggested Fix:</div>
                <div class="fix-text">${data.suggested_fix}</div>
            </div>

            <div style="margin-top: 20px; font-size: 0.8rem; color: #718096; text-align: center;">
                Extracted from Passbook: UAN: ${data.extracted_details.uan || 'N/A'}, Name: ${data.extracted_details.name || 'N/A'}
            </div>
            
            <button class="btn-sm" style="margin-top: 20px; width: 100%;" onclick="showPFVerification()">Verify Another</button>
        </div>
    `;
}

// Check status on load
if (token) {
    checkDocumentStatus();
}
