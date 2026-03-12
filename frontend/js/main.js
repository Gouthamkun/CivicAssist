// Auth Check & Logout Logic
if (!localStorage.getItem('civic_logged_in')) {
    window.location.href = 'login.html';
}

function logoutUser() {
    localStorage.removeItem('civic_logged_in');
    localStorage.removeItem('civic_current_user');
    window.location.href = 'login.html';
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
        const res = await fetch('http://localhost:8000/explain_notice', {
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
    const urgencyColor = urgency === 'urgent' ? '#e43137' : (urgency === 'attention' ? '#f7b900' : '#2b8a3e');
    const urgencyText = urgency.toUpperCase();
    
    modalBody.innerHTML = `
        <div class="ai-reasoning text-start">
            <div style="background-color: ${urgencyColor}; color: white; padding: 5px 15px; border-radius: 4px; display: inline-block; font-weight: bold; margin-bottom: 10px;">
                ${urgencyText}
            </div>
            <h3>${data.notice_type || 'Notice Analysis'}</h3>
            <p style="color: gray; font-size: 0.9em; margin-bottom: 20px;">Analyzed via CivicAssist OCR & AI</p>
            
            <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; line-height: 1.6;">
                <h5 style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 8px;"><i class="fa-solid fa-info-circle"></i> Explanation</h5>
                <p>${data.explanation || 'No detail provided.'}</p>
                
                ${data.why_received ? `
                    <h5 style="font-weight: bold; margin-top: 20px;"><i class="fa-solid fa-question-circle"></i> Why you received this</h5>
                    <p>${data.why_received}</p>
                ` : ''}

                ${data.steps && data.steps.length > 0 ? `
                    <h5 style="font-weight: bold; margin-top: 20px;"><i class="fa-solid fa-list-ol"></i> Action Steps</h5>
                    <ol style="padding-left: 20px;">
                        ${data.steps.map(s => `<li style="margin-bottom: 5px;">${s}</li>`).join('')}
                    </ol>
                ` : ''}

                ${data.forms_needed && data.forms_needed.length > 0 ? `
                    <h5 style="font-weight: bold; margin-top: 20px;"><i class="fa-solid fa-file-pdf"></i> Required Forms</h5>
                    <ul style="padding-left: 20px;">
                        ${data.forms_needed.map(f => `<li style="margin-bottom: 5px;">${f}</li>`).join('')}
                    </ul>
                ` : ''}

                ${data.official_links && data.official_links.length > 0 ? `
                    <h5 style="font-weight: bold; margin-top: 20px;"><i class="fa-solid fa-globe"></i> Official Portals</h5>
                    <ul style="padding-left: 20px;">
                        ${data.official_links.map(l => `<li style="margin-bottom: 5px;"><a href="${l}" target="_blank" style="color: var(--primary-red); overflow-wrap: break-word;">${l}</a></li>`).join('')}
                    </ul>
                ` : ''}

                ${data.what_if_ignore ? `
                    <div style="margin-top: 20px; padding: 15px; background-color: #fff5f5; border-left: 4px solid #e43137; border-radius: 4px; font-size: 0.9em;">
                        <i class="fa-solid fa-triangle-exclamation"></i> <strong>Consequence of Inaction:</strong> ${data.what_if_ignore}
                    </div>
                ` : ''}
                
                <div style="margin-top: 25px; border-top: 1px solid #eee; padding-top: 15px; text-align: center;">
                    <span style="font-weight: bold; color: #555;"><i class="fa-solid fa-phone"></i> Helpline: ${data.helpline || '1800-118-005'}</span>
                </div>
            </div>
        </div>
    `;
}
