const API_BASE = window.location.origin;

function logoutUser() {
    localStorage.removeItem('civic_logged_in');
    localStorage.removeItem('civic_current_user');
    localStorage.removeItem('civic_token');
    window.location.href = 'login.html';
}

async function fetchUserDocs() {
    try {
        const res = await fetch('/api/user_documents', {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        const data = await res.json();
        
        // Reset all to "Not Uploaded" first
        ['aadhaar', 'pan'].forEach(type => {
            const statusEl = document.getElementById(`status-${type}`);
            const actionEl = document.getElementById(`action-${type}`);
            if (statusEl) statusEl.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Not Uploaded';
            if (actionEl) {
                actionEl.innerHTML = `
                    <div class="doc-actions-row">
                        <label class="btn-upload">
                            <i class="fa-solid fa-upload"></i> Upload
                            <input type="file" onchange="uploadDocument('${type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display:none;">
                        </label>
                    </div>
                `;
            }
        });

        if (data.uploaded_types) {
             data.uploaded_types.forEach(type => {
                 const statusEl = document.getElementById(`status-${type}`);
                 const actionEl = document.getElementById(`action-${type}`);
                 
                 if (statusEl) {
                     statusEl.innerHTML = '<i class="fa-solid fa-circle-check" style="color: #00b074;"></i> Uploaded';
                 }
                 
                 if (actionEl) {
                     actionEl.innerHTML = `
                        <div class="doc-actions-row">
                            <button class="btn-link" onclick="viewDocument('${type}')"><i class="fa-solid fa-eye"></i> View</button>
                            <label class="btn-link" style="cursor:pointer;">
                                <i class="fa-solid fa-arrows-rotate"></i> Replace
                                <input type="file" onchange="uploadDocument('${type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display:none;">
                            </label>
                            <button class="btn-link" onclick="removeDocument('${type}')" style="color:#e43137;"><i class="fa-solid fa-trash"></i> Remove</button>
                            <button onclick="verifyIntegrity('${type}')" id="verify-btn-${type}" class="btn-sm" style="background:var(--accent-purple); color:white; border:none; border-radius:4px; padding:5px 10px; font-size: 0.8rem; margin-left: 10px;"><i class="fa-solid fa-shield-check"></i> Verify Integrity</button>
                        </div>
                     `;
                 }
             });
        }
    } catch (e) {
        console.error("Failed to fetch user docs:", e);
    }
}

function viewDocument(type) {
    const token = localStorage.getItem('civic_token');
    window.open(`/api/view_document/${type}?token=${token}`, '_blank');
}

async function removeDocument(type) {
    if(!confirm(`Are you sure you want to remove your ${type.toUpperCase()}?`)) return;
    
    try {
        const res = await fetch(`/api/remove_document/${type}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        const data = await res.json();
        if(data.success) {
            fetchUserDocs();
        } else {
            alert("Delete failed: " + data.detail);
        }
    } catch (e) {
        alert("Delete failed due to network error.");
    }
}

// Initial fetch
if (localStorage.getItem('civic_token')) {
    fetchUserDocs();
}

function toggleUserProfile() {
    const menu = document.getElementById('user-profile-menu');
    const isVisible = menu.style.display === 'block';

    if (!isVisible) {
        // Populate data
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

// Search and Chat logic
const searchInput = document.getElementById('ai-search-input');

function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    // Simulate AI thinking and response modal
    executeQuickQuery(query);
}

// Allow Enter key to search
searchInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

function executeQuickQuery(query) {
    searchInput.value = query;
    let knownForm = null;
    let knownLabel = null;

    // Map specific predefined queries to the physical downloaded forms
    if (query.includes('withdraw my PF') || query.includes('PF Withdrawal') || query.includes('pf withdrawal')) {
        knownForm = 'forms/PF Final Settlement.pdf';
        knownLabel = 'Download Form 19 (PF Withdrawal)';
    } else if (query.includes('transfer PF') || query.includes('pf transfer')) {
        knownForm = 'forms/PF Transfer.pdf';
        knownLabel = 'Download Form 13 (PF Transfer)';
    } else if (query.includes('pension') || query.includes('10d')) {
        knownForm = 'forms/Pension Claim.pdf';
        knownLabel = 'Download Form 10D (Pension Claim)';
    } else if (query.includes('lic') || query.includes('policy')) {
        knownForm = 'forms/LIC Policy Payment from PF.pdf';
        knownLabel = 'Download LIC Policy Form';
    }

    // Forcefully inject the mapped form directly into the payload processor
    simulateAIResponse(query, knownForm, knownLabel);
}

// Modal Logic
const modal = document.getElementById('ai-response-modal');
const modalBody = document.getElementById('ai-response-body');

function openModal() {
    modal.classList.add('active');
    // Prevent background scroll
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Close modal on outside click
window.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

async function simulateAIResponse(query, forceFormUrl = null, forceFormLabel = null) {
    const q = query.toLowerCase();

    let reasoningTitle = "Analysis Reasoning";
    if (q.includes("upload") || q.includes("document")) {
        reasoningTitle = '<i class="fa-solid fa-file-invoice"></i> OCR Document Analysis';
    }

    // Show loading state
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Analyzing query...</h3>
            <p>Processing over 7,500 document chunks. This may take 1-2 minutes on CPU.</p>
            <p style="font-size: 0.9rem; color: #666;">Retrieving official guidelines and forms...</p>
        </div>
    `;
    openModal();

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout

        const response = await fetch('/ask', {
            method: 'POST',
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: query })
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const aiResponse = data.response;

        // Build Action Button HTML if it exists natively OR if explicitly forced
        let actionButtonHtml = '';

        const finalUrl = forceFormUrl || aiResponse.action_url;
        const finalLabel = forceFormLabel || aiResponse.action_label;

        if (finalUrl && finalLabel && !finalLabel.toLowerCase().includes("not required")) {
            actionButtonHtml = `
                <div style="margin-top: 20px; text-align: left;">
                    <a href="${finalUrl}" target="_blank" class="btn btn-primary" style="display: inline-block; padding: 10px 20px; background-color: var(--primary-red); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <i class="fa-solid fa-download"></i> ${finalLabel}
                    </a>
                </div>
            `;
        } else if (finalLabel && finalLabel.toLowerCase().includes("not required")) {
            actionButtonHtml = `
                <div style="margin-top: 20px; text-align: left;">
                    <span style="display: inline-block; padding: 10px 20px; background-color: #f1f3f5; color: #495057; border: 1px solid #ced4da; border-radius: 5px; font-weight: bold; cursor: default;">
                        <i class="fa-solid fa-circle-info"></i> Form is not required
                    </span>
                </div>
            `;
        }

        let reqDocsHtml = '';
        if (aiResponse.required_documents && aiResponse.required_documents.length > 0) {
            reqDocsHtml = `
                <div style="margin-top: 15px;">
                    <h5 style="font-weight: bold;"><i class="fa-solid fa-file-contract"></i> Required Documents</h5>
                    <ul style="padding-left: 20px; text-align: left; list-style-type: disc;">
                        ${aiResponse.required_documents.map(d => `<li style="margin-bottom: 8px;">${d}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        let stepsHtml = '';
        if (aiResponse.steps && aiResponse.steps.length > 0) {
            stepsHtml = `
                <div style="margin-top: 15px;">
                    <h5 style="font-weight: bold;"><i class="fa-solid fa-list-ol"></i> Step-by-Step Process</h5>
                    <ol style="padding-left: 20px; text-align: left;">
                        ${aiResponse.steps.map(s => `<li style="margin-bottom: 8px;">${s}</li>`).join('')}
                    </ol>
                </div>
            `;
        }

        let mistakesHtml = '';
        if (aiResponse.common_mistakes && aiResponse.common_mistakes.length > 0) {
            mistakesHtml = `
                <div style="margin-top: 15px;">
                    <h5 style="color: var(--primary-red); font-weight: bold;"><i class="fa-solid fa-circle-exclamation"></i> Important Notes</h5>
                    <ul style="padding-left: 20px; text-align: left; list-style-type: disc;">
                        ${aiResponse.common_mistakes.map(m => `<li style="margin-bottom: 8px;">${m}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        let portalHtml = '';
        if (aiResponse.official_portal_link && aiResponse.official_portal_link !== "" && aiResponse.official_portal_link.toLowerCase() !== "not applicable") {
             portalHtml = `
                <div style="margin-top: 15px; text-align: left;">
                    <h5 style="font-weight: bold;"><i class="fa-solid fa-globe"></i> Official Portal Link</h5>
                    <a href="${aiResponse.official_portal_link}" target="_blank" style="color: var(--primary-red); text-decoration: underline; word-break: break-all;">${aiResponse.official_portal_link}</a>
                </div>
             `;
        }

        const answerText = aiResponse.overview ? aiResponse.overview.replace(/\n/g, '<br>') : (aiResponse.answer ? aiResponse.answer.replace(/\n/g, '<br>') : 'Information not found.');

        // Render the real AI response
        modalBody.innerHTML = `
            <div class="ai-reasoning text-start">
                <h4>${reasoningTitle}</h4>
                <p>I analyzed your query securely using the official government knowledge base.</p>
                ${aiResponse.official_source ? `<p style="font-size: 0.85em; color: gray;"><strong>Source:</strong> ${aiResponse.official_source}</p>` : ''}
            </div>
            <div class="ai-next-steps text-start">
                <div class="steps-container" style="white-space: pre-wrap; font-family: inherit; line-height: 1.6; padding: 15px; background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 10px;">
                    <div style="margin-bottom: 10px;">
                        <h5 style="font-weight: bold;"><i class="fa-solid fa-info-circle"></i> Overview</h5>
                        ${answerText}
                    </div>
                    ${reqDocsHtml}
                    ${stepsHtml}
                    ${mistakesHtml}
                    ${portalHtml}
                    ${actionButtonHtml}
                </div>
            </div>
        `;
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

// Service Card Logic

function openGeneralQueriesUI() {
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-clipboard-question" style="font-size: 3rem; color: var(--primary-red); margin-bottom: 20px;"></i>
            <h3>EPFO General Queries</h3>
            <p style="margin-top: 15px;">What specifically do you need help with regarding EPFO?</p>
            <div class="search-box glass-panel" style="margin-top: 20px; border: 1px solid var(--border-color); display: flex; padding: 5px; align-items: center; border-radius: 8px;">
                <input type="text" id="epfo-custom-query" placeholder="E.g., What is the process for PF withdrawal?" autocomplete="off" style="flex: 1; border: none; outline: none; padding: 10px; background: transparent;">
                <button class="btn btn-primary" onclick="submitEpfoQuery()" style="padding: 8px 16px; background-color: var(--primary-red); color: white; border: none; border-radius: 4px; cursor: pointer;">Ask AI</button>
            </div>
        </div>
    `;

    // Add enter key listener
    setTimeout(() => {
        const input = document.getElementById('epfo-custom-query');
        if (input) {
            input.focus();
            input.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') submitEpfoQuery();
            });
        }
    }, 100);
}

function submitEpfoQuery() {
    const input = document.getElementById('epfo-custom-query');
    let query = input ? input.value.trim() : "";

    // Check main background search bar if this is empty
    if (!query) {
        const globalInput = document.getElementById('ai-search-input');
        if (globalInput && globalInput.value.trim()) query = globalInput.value.trim();
    }

    if (!query) return;
    executeQuickQuery(query);
}

function openServiceModal(serviceName) {
    // Check if we have a specific template for this service
    const templateId = `${serviceName.toLowerCase()}-features-template`;
    const template = document.getElementById(templateId);

    if (template) {
        // Clear modal body and inject the template content
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    } else {
        // Default stubbed view for other services
        modalBody.innerHTML = `
            <div class="ai-reasoning text-center" style="text-align:center;">
                <i class="fa-solid fa-robot" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
                <h3>${serviceName} Assistant</h3>
                <p style="margin-top: 15px;">What specifically do you need help with regarding ${serviceName}?</p>
                <div class="search-box glass-panel" style="margin-top: 20px; border: 1px solid var(--border-color); display: flex; padding: 5px; align-items: center; border-radius: 8px;">
                    <input type="text" id="generic-custom-query" placeholder="Ask a question..." autocomplete="off" style="flex: 1; border: none; outline: none; padding: 10px; background: transparent;">
                    <button class="btn btn-gradient search-action" onclick="submitGenericQuery()" style="padding: 8px 16px; background-color: var(--primary-red); color: white; border: none; border-radius: 4px; cursor: pointer;">Ask AI</button>
                </div>
            </div>
        `;

        // Add enter key listener
        setTimeout(() => {
            const input = document.getElementById('generic-custom-query');
            if (input) {
                input.focus();
                input.addEventListener('keypress', function (e) {
                    if (e.key === 'Enter') submitGenericQuery();
                });
            }
        }, 100);
    }

    openModal();
}

function submitGenericQuery() {
    console.log("Ask AI clicked!");
    const input = document.getElementById('generic-custom-query');
    let query = input ? input.value.trim() : "";

    // Check main background search bar if this is empty
    if (!query) {
        console.log("Modal input is empty, checking global search bar...");
        const globalInput = document.getElementById('ai-search-input');
        if (globalInput && globalInput.value.trim()) {
            query = globalInput.value.trim();
        }
    }

    if (!query) {
        alert("Please enter a question in the search box to Ask AI.");
        return;
    }

    console.log("Executing Query:", query);
    executeQuickQuery(query);
}

function openUniversalNoticeExplainer() {
    openModal();
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center;">
            <i class="fa-solid fa-magnifying-glass-chart" style="font-size: 3rem; color: var(--primary-red); margin-bottom: 20px;"></i>
            <h3>Universal Notice Explainer</h3>
            <p style="margin-top: 15px;">Upload a Income Tax Notice, EPFO Rejection, or Passport Message (PDF/Image).</p>
            
            <div id="modal-upload-zone" style="border: 2px dashed #ccc; padding: 40px; margin-top: 20px; border-radius: 10px; cursor: pointer;">
                <i class="fa-solid fa-cloud-arrow-up" style="font-size: 2rem; color: #666; margin-bottom: 10px;"></i>
                <p id="modal-file-name">Drag & drop or Click to browse</p>
                <input type="file" id="modal-file-input" style="display:none;" accept="application/pdf,image/*">
            </div>
            
            <button class="btn btn-primary" onclick="submitUniversalNotice()" style="margin-top: 20px; width: 100%; padding: 12px; background-color: var(--primary-red); color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Official Document
            </button>
            
            <div id="modal-notice-loading" style="display:none; margin-top: 20px; color: #666;">
                <i class="fa-solid fa-file-invoice fa-bounce fa-2x"></i>
                <p>Running OCR & AI Analysis...</p>
            </div>
        </div>
    `;

    const zone = document.getElementById('modal-upload-zone');
    const input = document.getElementById('modal-file-input');
    
    zone.onclick = () => input.click();
    input.onchange = (e) => {
        if(e.target.files.length > 0) document.getElementById('modal-file-name').innerHTML = `<b>Selected:</b> ${e.target.files[0].name}`;
    };
    
    // Simple drag drop
    zone.ondragover = (e) => { e.preventDefault(); zone.style.borderColor = "var(--primary-red)"; };
    zone.ondragleave = () => { zone.style.borderColor = "#ccc"; };
    zone.ondrop = (e) => {
        e.preventDefault();
        input.files = e.dataTransfer.files;
        if(input.files.length > 0) document.getElementById('modal-file-name').innerHTML = `<b>Selected:</b> ${input.files[0].name}`;
        zone.style.borderColor = "#ccc";
    };
}

async function submitUniversalNotice() {
    const input = document.getElementById('modal-file-input');
    if (!input.files || input.files.length === 0) {
        alert("Please select a file first.");
        return;
    }

    const loading = document.getElementById('modal-notice-loading');
    loading.style.display = 'block';
    
    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
        const res = await fetch('/explain_notice', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        renderUniversalNoticeResult(data);
    } catch (e) {
        console.error(e);
        alert("Error analyzing notice.");
        loading.style.display = 'none';
    }
}

function renderUniversalNoticeResult(data) {
    const urgency = data.urgency || "normal";
    // Matching severity colors
    const severityColors = {
        'Low': '#2b8a3e',
        'Medium': '#f7b900',
        'High': '#e43137',
        'Critical': '#8b0000'
    };
    const statusColor = severityColors[data.severity_index] || '#2b8a3e';
    const urgencyText = (data.severity_index || urgency).toUpperCase();
    
    modalBody.innerHTML = `
        <div class="ai-reasoning text-start notice-intelligence-engine">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
                <div>
                   <div style="background-color: ${statusColor}; color: white; padding: 5px 15px; border-radius: 4px; display: inline-block; font-weight: bold; margin-bottom: 8px; font-size: 0.8rem;">
                        <i class="fa-solid fa-shield-halved"></i> SEVERITY: ${urgencyText}
                    </div>
                    <h2 style="font-size: 1.5rem; color: var(--text-dark); margin: 0;">${data.notice_type || 'Notice Analysis'}</h2>
                    <p style="color: #666; font-size: 0.9rem; margin: 4px 0;"><strong>Department:</strong> ${data.department || 'Government Wing'}</p>
                </div>
                <div style="text-align: right; background: #fff9db; border: 1px solid #fab005; padding: 10px 15px; border-radius: 8px;">
                    <span style="display: block; font-size: 0.7rem; color: #862e08; font-weight: bold; text-transform: uppercase;">Action Deadline</span>
                    <span style="font-size: 1.1rem; color: #c53030; font-weight: 700;">${data.deadline || 'N/A'}</span>
                </div>
            </div>

            <div class="intelligence-grid" style="display: grid; grid-template-columns: 1fr; gap: 20px;">
                <!-- Deep Reasoning Section -->
                <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                    <div style="background: #f8fafc; padding: 12px 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 10px;">
                        <i class="fa-solid fa-brain" style="color: var(--accent-purple);"></i>
                        <h4 style="margin: 0; font-weight: 700; color: #1e293b;">Notice Intelligence Analysis</h4>
                    </div>
                    <div style="padding: 20px;">
                        <div style="margin-bottom: 15px;">
                            <h5 style="color: #475569; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;">Simple Explanation</h5>
                            <p style="font-size: 1rem; line-height: 1.6; margin: 0;">${data.explanation || 'No summary available.'}</p>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #f1f5f9;">
                            <div>
                                <h5 style="color: #c53030; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;"><i class="fa-solid fa-triangle-exclamation"></i> Risk Analysis</h5>
                                <p style="font-size: 0.9rem; color: #4a5568; margin: 0;">${data.risk_analysis || 'No immediate risk data.'}</p>
                            </div>
                            <div>
                                <h5 style="color: #1e293b; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;"><i class="fa-solid fa-gavel"></i> Consequence</h5>
                                <p style="font-size: 0.9rem; color: #4a5568; margin: 0;">${data.consequence || 'Varies by department action.'}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Strategic Action Plan -->
                <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                    <div style="background: #f0fdf4; padding: 12px 20px; border-bottom: 1px solid #dcfce7; display: flex; align-items: center; gap: 10px;">
                        <i class="fa-solid fa-wand-magic-sparkles" style="color: #16a34a;"></i>
                        <h4 style="margin: 0; font-weight: 700; color: #166534;">Strategic Action Plan</h4>
                    </div>
                    <div style="padding: 20px;">
                         <div style="margin-bottom: 20px; background: #f0f9ff; padding: 15px; border-radius: 6px; border-left: 4px solid #0ea5e9;">
                            <h5 style="color: #0369a1; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 0.5px;">Recommended Strategy</h5>
                            <p style="font-size: 0.95rem; font-weight: 500; margin: 0;">${data.strategy || 'Follow the standard response protocol.'}</p>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <h5 style="color: #475569; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 0.5px;">Sequential Steps</h5>
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                ${(data.steps || []).map((step, idx) => `
                                    <div style="display: flex; gap: 12px; align-items: flex-start;">
                                        <span style="background: #e2e8f0; color: #475569; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0;">${idx + 1}</span>
                                        <p style="font-size: 0.95rem; margin: 0; color: #334155;">${step}</p>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <div style="margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
                            ${(data.forms_needed || []).map(form => `
                                <div style="background: #f1f5f9; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; color: #475569; border: 1px solid #e2e8f0; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-file-pdf"></i> ${form}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <div style="display: flex; gap: 15px; align-items: center; justify-content: center; padding: 15px; border-top: 1px solid #eee;">
                    <a href="${data.official_links?.[0] || '#'}" target="_blank" class="btn btn-primary" style="background: #1e293b; color: white; padding: 10px 25px; border-radius: 6px; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Official Portal
                    </a>
                    <span style="color: #64748b; font-size: 0.9rem;">Helpline: <strong>${data.helpline || '1800-118-005'}</strong></span>
                </div>
            </div>
        </div>
    `;
}

// ===== Extra Features: Grievance Generator =====

function openGrievanceGenerator() {
    const template = document.getElementById('grievance-generator-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
        openModal();
    }
}

async function generateGrievanceLetter() {
    const input = document.getElementById('grievance-input').value.trim();
    if (!input) return alert("Please describe your issue first.");

    const resultDiv = document.getElementById('grievance-letter-result');
    const contentDiv = document.getElementById('grievance-letter-content');
    
    contentDiv.innerHTML = "Generating formal letter using AI...";
    resultDiv.style.display = "block";

    try {
        const res = await fetch('/api/ask_tax_question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token'),
            },
            body: JSON.stringify({ question: `Write a formal government grievance letter for this issue: ${input}. Format it like a proper letter with dummy Sender/Receiver fields and a strong legal subject line.` })
        });
        const data = await res.json();
        // The endpoint returns a JSON with 'explanation' usually for the letter content
        const letter = data.explanation || data.answer || "Could not generate letter.";
        contentDiv.innerHTML = letter;
    } catch (e) {
        contentDiv.innerHTML = "Error generating letter. Please try again.";
    }
}

function copyGrievance() {
    const text = document.getElementById('grievance-letter-content').innerText;
    navigator.clipboard.writeText(text);
    alert("Letter copied to clipboard!");
}

// ===== Extra Features: Blockchain Verification =====

async function verifyIntegrity(docType) {
    const btn = document.getElementById(`verify-btn-${docType}`);
    const statusEl = document.getElementById(`status-${docType}`);
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking...';
    btn.disabled = true;

    try {
        const res = await fetch(`/api/verify_integrity/${docType}`, {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        const data = await res.json();
        
        if (data.authentic) {
            statusEl.innerHTML = '<i class="fa-solid fa-shield-check" style="color: #6f42c1;"></i> Verified (Blockchain Proof)';
            statusEl.style.color = "#6f42c1";
            alert(`✅ Integrity Verified!\n\nDocument hash matches the record on the blockchain.\n\nCurrent Hash: ${data.current_hash.substring(0,20)}...`);
        } else {
            statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: #e43137;"></i> TAMPERED';
            statusEl.style.color = "#e43137";
            alert(`❌ Integrity Failure!\n\nThe current file hash does NOT match the blockchain record.\n\nStored Hash: ${data.stored_hash}\nCurrent Hash: ${data.current_hash}`);
        }
    } catch (e) {
        alert("Verification service unavailable.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ===== Document Management =====

async function uploadDocument(type, input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('doc_type', type);
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload_document', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') },
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            fetchUserDocs(); // Refresh statuses
        } else {
            alert("Upload failed: " + data.detail);
        }
    } catch (e) {
        alert("Network error during upload.");
    } finally {
        input.value = '';
    }
}

// ===== EPFO PF Withdrawal Consolidation =====

function showPFOptions() {
    const template = document.getElementById('pf-options-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    }
}

function revertToEPFOGrid() {
    openServiceModal('EPFO');
}

async function showPFGuidance() {
    modalBody.innerHTML = `
        <div class="ai-reasoning text-center" style="text-align:center; padding: 40px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 20px;"></i>
            <h3>Personalizing Your Roadmap...</h3>
            <p>Fetching your document status and generating steps.</p>
        </div>
    `;

    try {
        const response = await fetch('/api/epfo/user-info', {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') }
        });
        const info = await response.json();
        
        // Use the guidance template
        const template = document.getElementById('pf-guidance-template');
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
        
        // Fill data
        document.getElementById('pf-guidance-name').innerText = info.name || "N/A";
        document.getElementById('pf-guidance-dob').innerText = info.dob || "N/A";
    } catch (error) {
        modalBody.innerHTML = `<div class='text-center'><h4>Error loading guidance</h4><button class='btn-outline' onclick='showPFOptions()'>Back</button></div>`;
    }
}

function showPFVerification() {
    const template = document.getElementById('pf-verification-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    }
}

async function verifyPassbook(input) {
    const file = input.files[0];
    if (!file) return;

    const resultContainer = document.getElementById('verification-result-container');
    const uploadText = document.getElementById('passbook-upload-text');
    
    uploadText.innerHTML = `<b>Selected:</b> ${file.name}`;
    resultContainer.innerHTML = `
        <div class="ai-reasoning text-center" style="padding:20px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary-red); margin-bottom: 10px;"></i>
            <p>Scanning Passbook & Matching Identity...</p>
        </div>
    `;
    resultContainer.style.display = "block";

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/epfo/verify-passbook', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('civic_token') },
            body: formData
        });
        const data = await response.json();
        
        const isSuccess = data.status === "Verified Successfully";
        const color = isSuccess ? "#00b074" : "#e43137";
        
        resultContainer.innerHTML = `
            <div style="border: 1px solid ${color}; padding: 20px; border-radius: 8px; margin-top: 25px; background: ${isSuccess ? '#f0fdf4' : '#fff5f5'}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); animation: fadeIn 0.5s ease-out;">
                <h4 style="color: ${color}; display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <i class="fa-solid ${isSuccess ? 'fa-circle-check' : 'fa-circle-exclamation'}" style="font-size: 1.4rem;"></i> 
                    ${data.status}
                </h4>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #eee; margin-bottom: 20px;">
                    <h5 style="margin-bottom: 10px; color: #555; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px;">Extracted Details from Passbook:</h5>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.95rem;">
                        <div><strong>Name:</strong> ${data.extracted_details.name || "Unknown"}</div>
                        <div><strong>UAN:</strong> ${data.extracted_details.uan || "N/A"}</div>
                        <div><strong>Member ID:</strong> ${data.extracted_details.member_id || "N/A"}</div>
                        <div><strong>DOB:</strong> ${data.extracted_details.dob || "N/A"}</div>
                    </div>
                </div>

                ${data.problems_found.length > 0 ? `
                    <div style="margin-bottom: 20px;">
                        <h5 style="color: #c53030; font-size: 0.9rem; margin-bottom: 8px;"><i class="fa-solid fa-triangle-exclamation"></i> Critical Mismatches Found:</h5>
                        <ul style="color: #e43137; padding-left: 20px; font-size: 0.9rem;">
                            ${data.problems_found.map(p => `<li style="margin-bottom: 4px;">${p}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid ${color};">
                    <h5 style="color: var(--text-dark); margin-bottom: 8px;"><i class="fa-solid fa-lightbulb" style="color: #ffd700;"></i> AI Recommendation & Roadmap:</h5>
                    <div style="font-size: 0.95rem; line-height: 1.5; color: #4a5568;">
                        ${data.suggested_fix.replace(/\n/g, '<br>')}
                    </div>
                </div>
                
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button class="btn-primary" style="flex: 1; padding: 10px; background: ${color};" onclick="closeModal()">Got it</button>
                    ${!isSuccess ? `<button class="btn-outline" style="flex: 1;" onclick="openGrievanceGenerator()">Report Issue</button>` : ''}
                </div>
            </div>
        `;
    } catch (e) {
        console.error(e);
        resultContainer.innerHTML = `
            <div style="background: #fff5f5; border: 1px solid #e43137; color: #e43137; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <i class="fa-solid fa-circle-xmark"></i> Verification failed. Please ensure the screenshot is clear and try again.
            </div>
        `;
    } finally {
        input.value = '';
    }
}
