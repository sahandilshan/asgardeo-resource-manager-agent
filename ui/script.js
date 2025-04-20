document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiUrlInput = document.getElementById('apiUrl');
    const orgNameInput = document.getElementById('orgName');
    const clientIdInput = document.getElementById('clientId');
    const clientSecretInput = document.getElementById('clientSecret');
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');

    // Application State
    let chatHistory = []; // Stores messages { role: 'user'/'agent', content: '...' }
    let isLoading = false; // Prevent multiple simultaneous requests

    // --- Helper Functions ---

    function displayMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);

        // Basic sanitation (replace with a proper library for production)
        // This prevents basic HTML injection but isn't fully secure.
        const sanitizedContent = content
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            // Convert newlines to <br> tags for display
             .replace(/\n/g, '<br>');

        // Use innerHTML carefully after basic sanitization and newline conversion
        // You could enhance this to handle markdown if needed
        messageDiv.innerHTML = sanitizedContent;

        // Add specific class for loading message styling
        if (role === 'loading') {
             messageDiv.classList.add('loading');
             messageDiv.setAttribute('id', 'loading-indicator'); // ID to remove it later
        }

        chatbox.appendChild(messageDiv);
        // Scroll to the bottom
        chatbox.scrollTop = chatbox.scrollHeight;
    }

     function removeLoadingIndicator() {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function setSendingState(sending) {
        isLoading = sending;
        userInput.disabled = sending;
        sendButton.disabled = sending;
        if (sending) {
            displayMessage('loading', 'Agent is thinking...');
        } else {
            removeLoadingIndicator();
        }
    }

    // --- Main Send Logic ---

    async function sendMessage() {
        const userMessageContent = userInput.value.trim();
        if (!userMessageContent || isLoading) {
            return; // Don't send empty messages or if already loading
        }

        // Get config values
        const apiUrl = apiUrlInput.value.trim();
        const orgName = orgNameInput.value.trim();
        const clientId = clientIdInput.value.trim();
        const clientSecret = clientSecretInput.value.trim(); // Get secret value

        if (!apiUrl || !orgName || !clientId || !clientSecret) {
            displayMessage('error', 'Please fill in all Configuration fields (API URL, Org Name, Client ID, Client Secret).');
            return;
        }

        // Display user message and add to history
        displayMessage('user', userMessageContent);
        chatHistory.push({ role: 'user', content: userMessageContent });
        userInput.value = ''; // Clear input

        setSendingState(true); // Show loading, disable input

        try {
            // Prepare API Key (Base64 encode clientId:clientSecret)
            const credentials = `${clientId}:${clientSecret}`;
            const base64ApiKey = btoa(credentials); // Browser's built-in Base64

            // Prepare payload
            const payload = {
                organization_name: orgName,
                chat: chatHistory
            };

            // Make API call
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'api-key': base64ApiKey // Send the base64 encoded key
                },
                body: JSON.stringify(payload)
            });

             removeLoadingIndicator(); // Remove loading indicator immediately after fetch returns

            if (!response.ok) {
                // Handle HTTP errors (like 4xx, 5xx)
                const errorText = await response.text(); // Get error details if possible
                throw new Error(`HTTP error! Status: ${response.status}. Details: ${errorText || 'No details provided.'}`);
            }

            // Process successful response
            const agentResponse = await response.json(); // { role: 'agent', content: '...' }
            if (agentResponse && agentResponse.content) {
                displayMessage('agent', agentResponse.content);
                chatHistory.push({ role: 'agent', content: agentResponse.content });
            } else {
                 displayMessage('error', 'Received an unexpected response format from the agent.');
            }

        } catch (error) {
            console.error('Error sending message:', error);
             removeLoadingIndicator(); // Ensure loading is removed on error
            displayMessage('error', `Failed to communicate with the agent. ${error.message}`);
             // Optional: Add failed message to history? Maybe not.
        } finally {
             // Re-enable input regardless of success or failure, unless already handled
             // Check isLoading flag again in case another process modified it
             if (isLoading) {
                 setSendingState(false);
             }
             userInput.focus(); // Focus back on input field
        }
    }

    // --- Event Listeners ---

    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keydown', (event) => {
        // Send message on Enter key, but allow Shift+Enter for newlines
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevent default newline insertion
            sendMessage();
        }
    });

    // Initial focus
    orgNameInput.focus(); // Focus on Org Name initially
});
