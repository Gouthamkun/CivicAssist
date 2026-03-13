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
if (searchInput) {
    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
}

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
    if (modal && e.target === modal) {
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
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token')
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

// -----------------------------------------------------------------------------
// Citizen Profile Memory Logic
// -----------------------------------------------------------------------------

function openTaxProfileModal() {
    const modal = document.getElementById('tax-profile-modal');
    if (modal) {
        modal.classList.add('active');
        // Hide existing global AI modal if open to prevent stacking
        const globalAiModal = document.getElementById('ai-response-modal');
        if (globalAiModal) globalAiModal.classList.remove('active');
        loadTaxProfile();
    }
}

function closeTaxProfileModal() {
    const modal = document.getElementById('tax-profile-modal');
    if (modal) modal.classList.remove('active');
}

async function loadTaxProfile() {
    const token = localStorage.getItem('civic_token');
    if (!token) return;

    try {
        const res = await fetch('/profile/get', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        if (res.ok) {
            const data = await res.json();
            if (data.employment_type) {
                document.getElementById('profile_employment_type').value = data.employment_type;
                document.getElementById('profile_salary_range').value = data.salary_range || "";
                document.getElementById('profile_senior_citizen').checked = !!data.senior_citizen;
                document.getElementById('profile_itr_filed').checked = !!data.itr_filed_last_year;

                // Show Summary
                const summaryDiv = document.getElementById('profile-summary-view');
                const summaryText = document.getElementById('profile-summary-text');
                if (summaryDiv && summaryText) {
                    summaryDiv.style.display = 'block';
                    summaryText.innerText = `Employment: ${data.employment_type}, Range: ${data.salary_range || 'N/A'}, Senior: ${data.senior_citizen ? 'Yes' : 'No'}`;
                }
            }
        }
    } catch(e) {
        console.error("Failed to load profile:", e);
    }
}

async function saveTaxProfile() {
    const token = localStorage.getItem('civic_token');
    if (!token) {
        alert("Please login to save your profile context.");
        return window.location.href = 'login.html';
    }

    const payload = {
        employment_type: document.getElementById('profile_employment_type').value,
        salary_range: document.getElementById('profile_salary_range').value,
        senior_citizen: document.getElementById('profile_senior_citizen').checked,
        itr_filed_last_year: document.getElementById('profile_itr_filed').checked
    };

    try {
        const res = await fetch('/profile/save', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            alert("Profile Context Saved! CivicAssist will now personalize its answers for you.");
            loadTaxProfile(); // Refresh to show info
        } else {
            alert("Failed to save profile.");
        }
    } catch(e) {
        console.error("Failed to save profile:", e);
    }
}

async function deleteTaxProfile() {
    const token = localStorage.getItem('civic_token');
    if (!token) return closeTaxProfileModal();

    if (!confirm("Are you sure you want to delete your contextual memory?")) return;

    try {
        await fetch('/profile/delete', {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        document.getElementById('taxProfileForm').reset();
        const summaryDiv = document.getElementById('profile-summary-view');
        if (summaryDiv) summaryDiv.style.display = 'none';
        alert("Profile memory cleared.");
        closeTaxProfileModal();
    } catch(e) {
        console.error("Failed to delete profile:", e);
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

function showPFProcessNavigator() {
    const template = document.getElementById('pf-process-nav-template');
    if (template) {
        modalBody.innerHTML = '';
        const clone = template.content.cloneNode(true);
        modalBody.appendChild(clone);
    }
}

async function submitPFProcessExplain(q) {
    if (!q) return;
    document.getElementById('pf_process_query').value = q;
    const loading = document.getElementById('pf_process_loading');
    const responseBox = document.getElementById('pf_process_response');
    
    loading.style.display = 'block';
    responseBox.style.display = 'none';
    
    try {
        const res = await fetch('/process_explain', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('civic_token')
            },
            body: JSON.stringify({ query: q })
        });
        const data = await res.json();
        renderProcessNavigatorResponse(data, 'pf_process_response');
    } catch (e) {
        console.error(e);
        responseBox.innerHTML = '<div style="color:red; padding:20px;">Error mapping process. Try a simpler keyword.</div>';
        responseBox.style.display = 'block';
    } finally {
        loading.style.display = 'none';
    }
}

function renderProcessNavigatorResponse(data, targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;

    const explanation = data.explanation || data.overview || "No detail provided.";
    const steps = data.next_steps || data.steps || [];
    const reqDocs = data.required_documents || [];
    
    let graphHtml = '';
    if (data.process_chain && data.process_chain.length > 0) {
        graphHtml = `
            <div class="process-flow" style="margin-bottom: 25px; background: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <h5 style="margin: 0 0 15px 0; font-size: 0.75rem; text-transform: uppercase; color: #64748b;"><i class="fa-solid fa-diagram-project"></i> Structural Process Path</h5>
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 10px;">
                    ${data.process_chain.map((step, idx) => `
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="padding: 6px 12px; background: ${step === data.current_step ? 'var(--primary-red)' : 'white'}; color: ${step === data.current_step ? 'white' : '#1e293b'}; border-radius: 6px; border: 1px solid ${step === data.current_step ? 'var(--primary-red)' : '#cbd5e1'}; font-weight: 600; font-size: 0.85rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                                ${step}
                            </div>
                            ${idx < data.process_chain.length - 1 ? '<i class="fa-solid fa-chevron-right" style="color: #cbd5e1; font-size: 0.8rem;"></i>' : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    let formsHtml = '';
    if (data.official_forms && data.official_forms.length > 0) {
        formsHtml = `
            <div style="margin-top: 15px; margin-bottom: 20px; padding: 12px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px;">
                <h5 style="margin: 0 0 8px 0; color: #795548; font-size: 0.75rem; text-transform: uppercase;"><i class="fa-solid fa-file-pdf"></i> Verified Official Forms</h5>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    ${data.official_forms.map(f => `
                        <a href="${f.url}" target="_blank" style="padding: 5px 12px; background: white; border: 1px solid #ffd54f; border-radius: 4px; color: #5d4037; font-size: 0.8rem; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-download"></i> ${f.name}
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
    }

    target.innerHTML = `
        <div class="rag-response" style="padding:20px;">
            ${graphHtml}
            ${formsHtml}
            <p style="font-size: 1rem; line-height: 1.6;">${explanation.replace(/\n/g, '<br>')}</p>
            ${reqDocs.length > 0 ? `<h4 style="margin-top:20px;">Required Documents</h4><ul>${reqDocs.map(d => `<li>${d}</li>`).join('')}</ul>` : ''}
            ${steps.length > 0 ? `<h4 style="margin-top:20px;">Lifecycle Steps</h4><ol>${steps.map(s => `<li>${s}</li>`).join('')}</ol>` : ''}
        </div>
    `;
    target.style.display = 'block';
}

// --- SMART FORM FILLING & FILING GUIDES ---

/**
 * Loads and displays all EPFO forms list in the main AI modal.
 * Called when user clicks "Smart Form Filling" in the EPFO panel.
 */
async function loadEPFOForms() {
    // Use the global modalBody = document.getElementById('ai-response-body')
    openModal();
    modalBody.innerHTML = `
        <div style="text-align:center; padding: 30px;">
            <i class="fa-solid fa-spinner fa-spin fa-2x" style="color: var(--primary-red);"></i>
            <p style="margin-top: 12px; color: #555;">Loading all EPFO forms...</p>
        </div>
    `;

    try {
        const res = await fetch('/api/forms/epfo');
        if (!res.ok) throw new Error('API error: ' + res.status);
        const forms = await res.json();

        if (!forms || forms.length === 0) {
            modalBody.innerHTML = '<p style="text-align:center; padding: 20px;">No forms available at the moment.</p>';
            return;
        }

        // Sort forms by name
        forms.sort((a, b) => a.name.localeCompare(b.name));

        let html = `
            <div style="padding: 5px 0;">
                <h3 style="margin-bottom: 8px; color: var(--primary-red); display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> EPFO Smart Form Filling
                </h3>
                <p style="margin-bottom: 20px; font-size: 0.9rem; color: #64748b; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px;">
                    Select a form to see a numbered, field-by-field filling guide. Numbers represent the order of blank fields in the actual form.
                </p>
                <div style="display: flex; flex-direction: column; gap: 12px;">
        `;

        forms.forEach(form => {
            const shortDesc = form.description.length > 100 ? form.description.slice(0, 97) + '...' : form.description;
            html += `
                <div class="form-item-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 15px; cursor:pointer; transition: all 0.2s;" 
                     onmouseover="this.style.borderColor='var(--primary-red)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)';"
                     onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none';">
                    <div style="flex: 1; min-width: 0;">
                        <h4 style="margin: 0 0 4px; color: #1e293b; font-size: 1rem; font-weight: 700;">${form.name}</h4>
                        <p style="margin: 0; font-size: 0.82rem; color: #64748b; line-height: 1.4;">${shortDesc}</p>
                    </div>
                    <div style="display: flex; gap: 8px; flex-shrink: 0;">
                        <button onclick="event.stopPropagation(); window.open('${form.pdf}', '_blank')" 
                                title="Download PDF"
                                style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 7px 10px; border-radius: 6px; font-size: 0.8rem; cursor: pointer; white-space:nowrap;">
                            <i class="fa-solid fa-download"></i> PDF
                        </button>
                        <button onclick="showFormFieldGuide('epfo', '${form.id}', '${form.name.replace(/'/g, "\\'")}')" 
                                style="background: var(--primary-red); color: white; border: none; padding: 7px 14px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; font-weight: 600; white-space:nowrap;">
                            <i class="fa-solid fa-list-ol"></i> Field Guide
                        </button>
                    </div>
                </div>
            `;
        });

        html += `</div></div>`;
        modalBody.innerHTML = html;

    } catch (e) {
        console.error("Error loading EPFO forms:", e);
        modalBody.innerHTML = `
            <div style="text-align:center; padding:40px; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                <p style="margin-top: 15px;">Failed to load forms. Check server connection.</p>
                <button class="btn-outline" onclick="loadEPFOForms()" style="margin-top: 15px;">Retry</button>
            </div>
        `;
    }
}

/**
 * Shows the numbered field-by-field guide for a specific EPFO form.
 * Renders inline in the current modal with a "Back to Forms" button.
 */
async function showFormFieldGuide(dept, formId, formName) {
    // Show loading state inside same modal
    modalBody.innerHTML = `
        <div style="text-align:center; padding: 40px;">
            <i class="fa-solid fa-spinner fa-spin fa-2x" style="color: var(--primary-red);"></i>
            <p style="margin-top: 12px; color: #555;">Loading guide for ${formName}...</p>
        </div>
    `;

    try {
        const res = await fetch(`/api/form-guide/${dept}/${formId}`);
        if (!res.ok) throw new Error('Guide not found');
        const data = await res.json();

        let html = `
            <div>
                <!-- Back nav -->
                <button onclick="loadEPFOForms()" class="modal-back-nav" style="display:flex; align-items:center; gap:6px; background:none; border:none; cursor:pointer; color: var(--primary-red); font-weight:600; font-size:0.9rem; margin-bottom: 16px; padding: 5px 0;">
                    <i class="fa-solid fa-arrow-left"></i> Back to All Forms
                </button>

                <!-- Header -->
                <div style="background: linear-gradient(135deg, var(--primary-red), #c0392b); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 6px; font-size: 1.3rem;"><i class="fa-solid fa-file-pen"></i> ${data.form_name}</h3>
                    <p style="margin: 0; opacity: 0.85; font-size: 0.9rem;">${data.description}</p>
                </div>

                <div style="margin-bottom: 12px; background: #fff8f1; border: 1px solid #fed7aa; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; color: #92400e;">
                    <i class="fa-solid fa-info-circle"></i> Each number below represents a <strong>blank field in the form</strong>, in the order they appear.
                </div>

                <!-- Fields list -->
                <div style="display: flex; flex-direction: column; gap: 10px;">
        `;

        data.fields.forEach(field => {
            html += `
                <div style="display: flex; gap: 14px; align-items: flex-start; background: #f8fafc; padding: 14px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="background: var(--primary-red); color: white; min-width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.9rem; flex-shrink: 0;">
                        ${field.number}
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; color: #1e293b; font-size: 0.95rem; margin-bottom: 3px;">${field.name}</div>
                        <div style="font-size: 0.88rem; color: #475569; line-height: 1.5;">${field.description}</div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
                <div style="display: flex; gap: 10px; margin-top: 20px; padding-top: 15px; border-top: 1px solid #f1f5f9;">
                    <button onclick="window.open('${data.pdf}', '_blank')" style="flex:1; padding: 11px; background: #1e293b; color: white; border: none; border-radius: 7px; cursor:pointer; font-weight: 600; display:flex; align-items:center; justify-content:center; gap:8px;">
                        <i class="fa-solid fa-file-pdf"></i> Download Official Form (PDF)
                    </button>
                    <button onclick="loadEPFOForms()" style="padding: 11px 18px; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 7px; cursor:pointer; font-weight: 600;">
                        <i class="fa-solid fa-grid-2"></i> All Forms
                    </button>
                </div>
            </div>
        `;

        modalBody.innerHTML = html;

    } catch (e) {
        console.error('Error loading form guide:', e);
        modalBody.innerHTML = `
            <div style="text-align:center; padding:30px; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                <p style="margin-top: 15px;">No guide found for this form. Try using the PDF download.</p>
                <button class="btn-outline" onclick="loadEPFOForms()" style="margin-top: 15px;"><i class="fa-solid fa-arrow-left"></i> Back to Forms</button>
            </div>
        `;
    }
}

/**
 * Loads and displays the list of Income Tax forms in the Filing Guide tab.
 */
async function loadITForms() {
    openModal();
    modalBody.innerHTML = `
        <div style="text-align:center; padding: 30px;">
            <i class="fa-solid fa-spinner fa-spin fa-2x" style="color: var(--primary-red);"></i>
            <p style="margin-top: 12px; color: #555;">Loading all ITR forms...</p>
        </div>
    `;

    try {
        const res = await fetch('/api/forms/income-tax');
        if (!res.ok) throw new Error('API error: ' + res.status);
        const forms = await res.json();

        if (!forms || forms.length === 0) {
            modalBody.innerHTML = '<p style="text-align:center; padding: 20px;">No forms available at the moment.</p>';
            return;
        }

        forms.sort((a, b) => a.name.localeCompare(b.name));

        let html = `
            <div style="padding: 5px 0;">
                <h3 style="margin-bottom: 8px; color: var(--primary-red); display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-file-invoice-dollar"></i> ITR Filing Guides
                </h3>
                <p style="margin-bottom: 20px; font-size: 0.9rem; color: #64748b; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px;">
                    Select a form to see a numbered, field-by-field filling guide. Numbers represent the order of blank fields in the actual form.
                </p>
                <div style="display: flex; flex-direction: column; gap: 12px;">
        `;

        forms.forEach(form => {
            const shortDesc = form.description.length > 100 ? form.description.slice(0, 97) + '...' : form.description;
            html += `
                <div class="form-item-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 15px; cursor:pointer; transition: all 0.2s;" 
                     onmouseover="this.style.borderColor='var(--primary-red)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)';"
                     onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none';">
                    <div style="flex: 1; min-width: 0;">
                        <h4 style="margin: 0 0 4px; color: #1e293b; font-size: 1rem; font-weight: 700;">${form.name}</h4>
                        <p style="margin: 0; font-size: 0.82rem; color: #64748b; line-height: 1.4;">${shortDesc}</p>
                    </div>
                    <div style="display: flex; gap: 8px; flex-shrink: 0;">
                        <button onclick="event.stopPropagation(); window.open('${form.pdf}', '_blank')" 
                                title="Download PDF"
                                style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 7px 10px; border-radius: 6px; font-size: 0.8rem; cursor: pointer; white-space:nowrap;">
                            <i class="fa-solid fa-download"></i> PDF
                        </button>
                        <button onclick="showITFormGuide('${form.id}', '${form.name.replace(/'/g, "\\'")}')" 
                                style="background: var(--primary-red); color: white; border: none; padding: 7px 14px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; font-weight: 600; white-space:nowrap;">
                            <i class="fa-solid fa-list-ol"></i> Field Guide
                        </button>
                    </div>
                </div>
            `;
        });

        html += `</div></div>`;
        modalBody.innerHTML = html;

    } catch (e) {
        console.error("Error loading IT forms:", e);
        modalBody.innerHTML = `
            <div style="text-align:center; padding:40px; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                <p style="margin-top: 15px;">Failed to load forms. Check server connection.</p>
                <button class="btn-outline" onclick="loadITForms()" style="margin-top: 15px;">Retry</button>
            </div>
        `;
    }
}

/**
 * Shows the field guide for an IT form inline in the modal.
 */
async function showITFormGuide(formId, formName) {
    modalBody.innerHTML = `
        <div style="text-align:center; padding: 40px;">
            <i class="fa-solid fa-spinner fa-spin fa-2x" style="color: var(--primary-red);"></i>
            <p style="margin-top: 12px; color: #555;">Loading guide for ${formName}...</p>
        </div>
    `;

    try {
        const res = await fetch(`/api/form-guide/income-tax/${formId}`);
        if (!res.ok) throw new Error('Guide not found');
        const data = await res.json();

        let html = `
            <div>
                <!-- Back nav -->
                <button onclick="loadITForms()" class="modal-back-nav" style="display:flex; align-items:center; gap:6px; background:none; border:none; cursor:pointer; color: var(--primary-red); font-weight:600; font-size:0.9rem; margin-bottom: 16px; padding: 5px 0;">
                    <i class="fa-solid fa-arrow-left"></i> Back to All Forms
                </button>

                <!-- Header -->
                <div style="background: linear-gradient(135deg, var(--primary-red), #c0392b); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 6px; font-size: 1.3rem;"><i class="fa-solid fa-file-pen"></i> ${data.form_name}</h3>
                    <p style="margin: 0; opacity: 0.85; font-size: 0.9rem;">${data.description}</p>
                </div>

                <div style="margin-bottom: 12px; background: #fff8f1; border: 1px solid #fed7aa; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; color: #92400e;">
                    <i class="fa-solid fa-info-circle"></i> Each number below represents a <strong>blank field in the form</strong>, in the order they appear.
                </div>

                <!-- Fields list -->
                <div style="display: flex; flex-direction: column; gap: 10px;">
        `;

        data.fields.forEach(field => {
            html += `
                <div style="display: flex; gap: 14px; align-items: flex-start; background: #f8fafc; padding: 14px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="background: var(--primary-red); color: white; min-width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.9rem; flex-shrink: 0;">
                        ${field.number}
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; color: #1e293b; font-size: 0.95rem; margin-bottom: 3px;">${field.name}</div>
                        <div style="font-size: 0.88rem; color: #475569; line-height: 1.5;">${field.description}</div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
                <div style="display: flex; gap: 10px; margin-top: 20px; padding-top: 15px; border-top: 1px solid #f1f5f9;">
                    <button onclick="window.open('${data.pdf}', '_blank')" style="flex:1; padding: 11px; background: #1e293b; color: white; border: none; border-radius: 7px; cursor:pointer; font-weight: 600; display:flex; align-items:center; justify-content:center; gap:8px;">
                        <i class="fa-solid fa-file-pdf"></i> Download Official Form (PDF)
                    </button>
                    <button onclick="loadITForms()" style="padding: 11px 18px; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 7px; cursor:pointer; font-weight: 600;">
                        <i class="fa-solid fa-grid-2"></i> All Forms
                    </button>
                </div>
            </div>
        `;

        modalBody.innerHTML = html;

    } catch (e) {
        console.error('Error loading form guide:', e);
        modalBody.innerHTML = `
            <div style="text-align:center; padding:30px; color: var(--primary-red);">
                <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                <p style="margin-top: 15px;">No guide found for this form. Try using the PDF download.</p>
                <button class="btn-outline" onclick="loadITForms()" style="margin-top: 15px;"><i class="fa-solid fa-arrow-left"></i> Back to Forms</button>
            </div>
        `;
    }
}

/**
 * Legacy viewFormGuide — kept for compatibility, routes to showFormFieldGuide/showITFormGuide.
 */
async function viewFormGuide(dept, formId) {
    if (dept === 'epfo') {
        await showFormFieldGuide(dept, formId, formId.toUpperCase());
    } else {
        await showITFormGuide(formId, formId.toUpperCase());
    }
}

// ===== PASSPORT TRACKING LOGIC =====

function showPassportTracking() {
    const template = document.getElementById('passport-tracking-template');
    if (!template) return;
    
    modalBody.innerHTML = '';
    modalBody.appendChild(template.content.cloneNode(true));
    
    // Check if tracking is already active
    updatePassportStatusView();
}

async function updatePassportStatusView() {
    const token = localStorage.getItem('civic_token');
    try {
        const response = await fetch('/api/passport_status', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await response.json();
        
        if (data.tracking && !data.passport_received) {
            document.getElementById('passport-track-form-container').style.display = 'none';
            document.getElementById('passport-active-monitor').style.display = 'block';
            
            const appDate = new Date(data.application_date);
            const today = new Date();
            const diffDays = Math.floor((today - appDate) / (1000 * 60 * 60 * 24));
            
            document.getElementById('monitor-days').innerText = `Application age: ${diffDays} days (${data.application_type})`;
            
            if (data.delayed) {
                document.getElementById('passport-status-shield').innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: #c53030;"></i>';
                document.getElementById('monitor-heading').innerText = 'Delay Possible';
                document.getElementById('delay-action-box').style.display = 'block';
            } else {
                document.getElementById('passport-status-shield').innerHTML = '<i class="fa-solid fa-clock fa-spin" style="color: #3b82f6;"></i>';
                document.getElementById('monitor-heading').innerText = 'Monitoring Timeline';
                document.getElementById('delay-action-box').style.display = 'none';
            }
        } else {
            showPassportTrackForm();
        }
    } catch (e) {
        console.error("Failed to fetch passport status", e);
    }
}

function showPassportTrackForm() {
    document.getElementById('passport-track-form-container').style.display = 'block';
    document.getElementById('passport-active-monitor').style.display = 'none';
    document.getElementById('grievance-draft-container').style.display = 'none';
}

async function savePassportTracking() {
    const payload = {
        application_date: document.getElementById('pass_app_date').value,
        application_type: document.getElementById('pass_app_type').value,
        police_verification: document.getElementById('pass_police_status').value
    };
    
    const token = localStorage.getItem('civic_token');
    try {
        const res = await fetch('/api/track_passport', {
            method: 'POST',
            headers: { 
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            updatePassportStatusView();
        } else {
            alert("Failed to start tracking.");
        }
    } catch (e) {
        alert("Error connecting to server.");
    }
}

async function resolvePassport() {
    if (!confirm("Congratulations! Click OK to stop monitoring and mark your passport as received.")) return;
    
    const token = localStorage.getItem('civic_token');
    try {
        await fetch('/api/resolve_passport', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        openServiceModal('Passport');
    } catch (e) {
        console.error(e);
    }
}

async function generatePassportGrievance() {
    const container = document.getElementById('grievance-draft-container');
    const content = document.getElementById('passport-grievance-content');
    
    content.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI is drafting your formal grievance letter...';
    container.style.display = 'block';
    
    const token = localStorage.getItem('civic_token');
    try {
        const response = await fetch('/api/generate_passport_grievance', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await response.json();
        content.innerText = data.draft;
    } catch (e) {
        content.innerText = "Error generating draft. Please try again later.";
    }
}

function copyPassportGrievance() {
    const txt = document.getElementById('passport-grievance-content').innerText;
    navigator.clipboard.writeText(txt).then(() => {
        alert("Grievance draft copied to clipboard!");
    });
}

async function testPassportAlert() {
    const token = localStorage.getItem('civic_token');
    if (!token) return;

    if (!confirm("This will trigger a REAL phone call and email to your registered details. Proceed with the demo?")) return;

    // Show loading on the button
    const btn = event.currentTarget;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initiating Alert...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/test_passport_alert', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
        } else {
            alert("Failed to initiate demo alert. Check server logs.");
        }
    } catch (e) {
        console.error(e);
        alert("Network error.");
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}
