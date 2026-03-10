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
            <p>Please wait while CivicAssist retrieves the information securely.</p>
        </div>
    `;
    openModal();

    try {
        const response = await fetch('http://127.0.0.1:8000/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: query })
        });

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

        // Render the real AI response
        modalBody.innerHTML = `
            <div class="ai-reasoning">
                <h4>${reasoningTitle}</h4>
                <p>I analyzed your query securely using the government knowledge base.</p>
            </div>
            <div class="ai-next-steps">
                <h4><i class="fa-solid fa-shoe-prints"></i> Recommended Next Steps</h4>
                <div class="steps-container" style="white-space: pre-wrap; font-family: inherit; line-height: 1.6; padding: 10px;">
                    ${aiResponse.answer.replace(/\n/g, '<br>')}
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
    if (!input || !input.value.trim()) return;
    executeQuickQuery(input.value.trim());
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
                <div class="search-box glass-panel" style="margin-top: 20px; border: 1px solid var(--border-color);">
                    <input type="text" placeholder="Ask a question..." autocomplete="off">
                    <button class="btn btn-gradient search-action" style="padding: 8px 16px; background-color: var(--primary-red); color: white;">Ask AI</button>
                </div>
            </div>
        `;
    }

    openModal();
}
