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
const noticeInput = document.getElementById('notice-upload-input');

function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;
    executeGuidanceQuery(query);
}

function triggerNoticeUpload() {
    noticeInput.click();
}

async function handleNoticeUpload(input) {
    const file = input.files[0];
    if (!file) return;

    // Show loading state
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Scanning Document...</h3>
            <p>Processing ${file.name} with OCR and Domain Classification.</p>
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

        if (!response.ok) throw new Error('Failed to process notice');

        const data = await response.json();
        renderStructuredResponse(data, "Notice Explainer Result");
    } catch (error) {
        renderError("Could not process the notice. Please ensure the backend is running and the file is valid.");
    } finally {
        input.value = ''; // Reset input
    }
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

// ===== AI Response Logic =====
async function executeGuidanceQuery(query) {
    // Show loading state
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Consulting Knowledge Base...</h3>
            <p>Retrieving official guidance regarding your query.</p>
        </div>
    `;
    openModal();

    try {
        // Use the new tax question pipeline
        const response = await fetch(API_BASE + '/api/ask_tax_question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token'),
            },
            body: JSON.stringify({ question: query })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        renderStructuredResponse(data, "AI Guidance Response");
    } catch (error) {
        console.error("Error communicating with AI:", error);
        renderError("Could not connect to the CivicAssist RAG backend.");
    }
}

function renderStructuredResponse(data, title) {
    const deadlineHtml = data.deadline 
        ? `<div class="deadline-alert" style="background: #fff3cd; border-left: 5px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 4px;">
            <strong><i class="fa-solid fa-clock"></i> Important Deadline:</strong> ${data.deadline}
           </div>` 
        : '';

    const stepsHtml = data.steps && data.steps.length > 0 
        ? `<div class="ai-next-steps">
            <h4><i class="fa-solid fa-shoe-prints"></i> Recommended Next Steps</h4>
            <ul style="padding-left: 20px; line-height: 1.6;">
                ${data.steps.map(step => `<li>${step}</li>`).join('')}
            </ul>
           </div>`
        : '';

    const sourcesHtml = data.sources && data.sources.length > 0
        ? `<div class="sources-list" style="margin-top: 15px; font-size: 0.8rem; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
            <strong>Sources:</strong> ${data.sources.join(', ')}
           </div>`
        : '';

    const subTitle = data.notice_type 
        ? ` <span class="tag" style="background: var(--primary-red); color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; vertical-align: middle; margin-left: 10px;">${data.notice_type}</span>`
        : (data.query_type ? ` <span class="tag" style="background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; vertical-align: middle; margin-left: 10px;">${data.query_type.replace('_', ' ')}</span>` : '');

    modalBody.innerHTML = `
        <div class="ai-reasoning">
            <h4 style="display: flex; align-items: center; justify-content: space-between;">
                ${title}
                ${subTitle}
            </h4>
            <p style="white-space: pre-wrap; margin-top: 10px;">${data.explanation}</p>
        </div>
        ${deadlineHtml}
        ${stepsHtml}
        <div class="recommended-action" style="margin-top: 20px; font-weight: bold; color: var(--primary-red);">
            <i class="fa-solid fa-star"></i> Pro-Tip: ${data.recommended_action}
        </div>
        ${sourcesHtml}
    `;
}

function renderError(message) {
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center; color: var(--primary-red);">
            <i class="fa-solid fa-triangle-exclamation" style="font-size: 3rem; margin-bottom: 20px;"></i>
            <h3>Error</h3>
            <p>${message}</p>
        </div>
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

// ===== PF Withdrawal Feature Extension =====

function openPFWithdrawalModes() {
    const template = document.getElementById('pf-withdrawal-modes-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    }
}

function renderPFVerificationView() {
    const template = document.getElementById('pf-verification-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    }
}

async function renderPFGuidanceView() {
    // Show loading state first
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center; padding: 40px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Personalizing Your Roadmap...</h3>
            <p>Fetching your document status and generating steps.</p>
        </div>
    `;

    try {
        const response = await fetch(API_BASE + '/api/epfo/user-info', {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        const info = await response.json();
        
        const name = info.name || "Citizen";
        const hasDocs = info.source !== "registration";

        modalBody.innerHTML = `
            <div class="guidance-view" style="padding: 10px;">
                <h3 style="margin-bottom: 20px; color: var(--primary-red); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;">
                    <i class="fa-solid fa-map-location-dot"></i> PF Withdrawal Roadmap
                </h3>
                
                <div class="welcome-box" style="background: #e9ecef; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                    <h4>Welcome, ${name}!</h4>
                    <p style="margin-top: 5px;">Based on your profile, here is your path to a successful PF withdrawal.</p>
                    ${!hasDocs ? `<p style="margin-top: 10px; color: #856404; font-size: 0.9rem;"><strong>Tip:</strong> Uploading your Aadhaar/PAN in the dashboard helps us give more precise guidance.</p>` : ''}
                </div>

                <div class="roadmap-steps">
                    <div class="step-card">
                        <div class="step-number">1</div>
                        <div class="step-details">
                            <h4 style="color: var(--primary-blue);">Verify Eligibility</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted);">Ensure you have completed 6 months of service for pension withdrawal or 5 years for tax-free PF withdrawal (if not retired).</p>
                        </div>
                    </div>
                    <div class="step-card">
                        <div class="step-number">2</div>
                        <div class="step-details">
                            <h4 style="color: var(--primary-blue);">Check KYC Status</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted);">Log in to UAN Portal and ensure Aadhaar, PAN, and Bank Account are 'Digitally Approved' by your employer.</p>
                        </div>
                    </div>
                    <div class="step-card">
                        <div class="step-number">3</div>
                        <div class="step-details">
                            <h4 style="color: var(--primary-blue);">Submit Claim (Form 19/31/10C)</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted);">Select Form 31 for Advance (during job) or Form 19 & 10C for full settlement (after leaving job).</p>
                        </div>
                    </div>
                    <div class="step-card" style="border-bottom: none;">
                        <div class="step-number">4</div>
                        <div class="step-details">
                            <h4 style="color: var(--primary-blue);">Track & Receive</h4>
                            <p style="font-size: 0.9rem; color: var(--text-muted);">Claims usually take 7-15 working days. Funds are directly deposited into your linked bank account.</p>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 30px; display: flex; gap: 10px;">
                    <button class="btn-outline" onclick="openPFWithdrawalModes()" style="flex: 1;">Back</button>
                    <button class="btn-primary" onclick="executeQuickQuery('How to apply for PF withdrawal online?')" style="flex: 2;">Detailed How-To Guide</button>
                </div>
            </div>
        `;
    } catch (error) {
        renderError("Failed to load personalized guidance. Please try again later.");
    }
}

async function handlePassbookUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const resultContainer = document.getElementById('verification-result-container');
    const dropZone = document.getElementById('passbook-drop-zone');
    
    // Show loading in result container
    resultContainer.innerHTML = `
        <div class="text-center" style="padding: 20px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-purple); margin-bottom: 10px;"></i>
            <p>AI is analyzing passbook details...</p>
        </div>
    `;
    
    // Dim drop zone
    dropZone.style.opacity = '0.5';
    dropZone.style.pointerEvents = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(API_BASE + '/api/epfo/verify-passbook', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') },
            body: formData
        });

        if (!response.ok) throw new Error("Verification failed");

        const data = await response.json();
        renderPFVerificationResult(data);
    } catch (error) {
        resultContainer.innerHTML = `
            <div class="alert alert-danger" style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px;">
                <i class="fa-solid fa-circle-xmark"></i> Error: Could not process the passbook. Ensure it's a clear image of the profile page.
            </div>
        `;
    } finally {
        dropZone.style.opacity = '1';
        dropZone.style.pointerEvents = 'auto';
        input.value = '';
    }
}

function renderPFVerificationResult(data) {
    const container = document.getElementById('verification-result-container');
    const isSuccess = data.status === "Verified Successfully";
    const statusColor = isSuccess ? "#00b074" : "#e43137";
    const icon = isSuccess ? "fa-circle-check" : "fa-circle-exclamation";
    
    let problemsHtml = '';
    if (data.problems_found && data.problems_found.length > 0) {
        problemsHtml = `
            <div style="margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">
                <h5 style="color: #666; font-size: 0.9rem; margin-bottom: 8px;">Problems Found:</h5>
                <ul style="padding-left: 20px; color: var(--text-dark); font-size: 0.9rem; line-height: 1.6;">
                    ${data.problems_found.map(p => `<li>${p}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="result-card" style="border: 1px solid ${statusColor}; border-radius: 8px; overflow: hidden; animation: slideIn 0.3s ease-out; margin-top: 20px;">
            <div style="background: ${statusColor}; color: white; padding: 15px 20px; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid ${icon}" style="font-size: 1.2rem;"></i>
                    <h4 style="margin: 0;">Verification Result: ${data.status}</h4>
                </div>
            </div>
            <div style="padding: 20px; background: white;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px;">
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; text-align: center;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">UAN Number</div>
                        <div style="font-weight: 500; font-size: 0.9rem;">${data.extracted_details.uan || "N/A"}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; text-align: center;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Member Name</div>
                        <div style="font-weight: 500; font-size: 0.9rem;">${data.extracted_details.name || "Not Found"}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; text-align: center;">
                        <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">DOB</div>
                        <div style="font-weight: 500; font-size: 0.9rem;">${data.extracted_details.dob || "Not Found"}</div>
                    </div>
                </div>
                
                ${problemsHtml}
                
                <div style="margin-top: 20px; padding: 15px; background: ${isSuccess ? '#f0fdf4' : '#fff5f5'}; border-radius: 8px; border-left: 4px solid ${statusColor};">
                    <h5 style="margin-bottom: 5px; color: ${statusColor};"><i class="fa-solid fa-circle-info"></i> Suggested Fix:</h5>
                    <p style="font-size: 0.95rem; line-height: 1.5; color: var(--text-dark); margin: 0;">
                        ${data.suggested_fix}
                    </p>
                </div>
                
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button class="btn-outline" onclick="renderPFVerificationView()" style="flex: 1;">Re-Upload</button>
                    ${isSuccess ? `<button class="btn-primary" style="flex: 2;">Continue to Claim</button>` : `<button class="btn-primary" style="flex: 2; background: #6c757d;">Fix on EPFO Portal</button>`}
                </div>
            </div>
        </div>
    `;
}
