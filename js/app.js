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
document.addEventListener('click', function(event) {
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

// AI Simulation Data
const simulatedResponses = {
    'upload pf rejection notice': {
        reasoning: "I ran OCR on the uploaded document. The rejection notice states: <strong>'REJECTED: MEMBER AADHAAR NOT SEEDED AGAINST UAN'</strong>.",
        steps: [
            "Log in to the EPFO unified member portal using your UAN and password.",
            "Go to the 'Manage' tab and click on 'KYC'.",
            "Select 'Aadhaar', enter your Aadhaar number and name exactly as per Aadhaar.",
            "Save and wait for your employer to digitally approve the KYC.",
            "Once approved, you can resubmit your Form 19 for PF withdrawal."
        ]
    },
    'how do i link aadhaar to uan?': {
        reasoning: "Linking Aadhaar to UAN is mandatory for PF withdrawals and access to online services.",
        steps: [
            "Visit the EPFO Member e-Sewa portal and log in with your UAN.",
            "Navigate to Manage > KYC.",
            "Add your Aadhaar details and save.",
            "Contact your employer to digitally approve the KYC request using their DSC."
        ]
    },
    'why is my passport delayed?': {
        reasoning: "Usually, normal passports take around 30 days to arrive after police verification. Delays often happen due to pending police verification or discrepancies in documents.",
        steps: [
            "Check your application status on the Passport Seva portal using your File Number.",
            "If it shows 'Pending Police Verification', contact your local police station.",
            "If it exceeds 45 days with no status change, raise a grievance on the portal's 'Grievance' tab.",
            "Schedule an appointment at the RPO (Regional Passport Office) as a last resort."
        ]
    },
    'default': {
        reasoning: "I analyzed your query securely using the government knowledge base.",
        steps: [
            "Verify your eligibility on the respective official portal.",
            "Ensure all required KYC documents (Aadhaar, PAN) are updated.",
            "Submit the required form online.",
            "Track the status of your application via their tracking tools."
        ]
    }
};

function simulateAIResponse(query) {
    const q = query.toLowerCase();
    
    // Simple exact match logic for simulation
    let responseData = simulatedResponses['default'];
    for (const key in simulatedResponses) {
        if (q.includes(key.toLowerCase()) || key.toLowerCase().includes(q)) {
            responseData = simulatedResponses[key];
            break;
        }
    }

    // specific case for document mock upload
    let reasoningTitle = "Analysis Reasoning";
    if (q.includes("upload") || q.includes("document")) {
        reasoningTitle = '<i class="fa-solid fa-file-invoice"></i> OCR Document Analysis';
    }

    // Build Modal Content (Showing the Thinking -> Steps)
    modalBody.innerHTML = `
        <div class="ai-reasoning">
            <h4>${reasoningTitle}</h4>
            <p>${responseData.reasoning}</p>
        </div>
        <div class="ai-next-steps">
            <h4><i class="fa-solid fa-shoe-prints"></i> Recommended Next Steps</h4>
            <div class="steps-container">
                ${responseData.steps.map((step, index) => `
                    <div class="step-card">
                        <div class="step-number">${index + 1}</div>
                        <div class="step-desc">${step}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    openModal();
}

// Service Card Logic
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
