// Global variables
let token = '';
// No API_URL prefix needed - the endpoints are already at the root

// DOM Elements
const loginForm = document.getElementById('loginForm');
const dashboard = document.getElementById('dashboard');
const accountsTable = document.getElementById('accountsTable');
const transactionsTable = document.getElementById('transactionsTable');
const usersTable = document.getElementById('usersTable');
const saveAccountBtn = document.getElementById('saveAccountBtn');
const saveTransactionBtn = document.getElementById('saveTransactionBtn');
const saveUserBtn = document.getElementById('saveUserBtn');
const addEntryBtn = document.getElementById('addEntryBtn');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Check if token exists in localStorage
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
        token = storedToken;
        showDashboard();
    }

    // Login form submission
    loginForm.addEventListener('submit', handleLogin);

    // Tab change events to load data
    document.getElementById('accounts-tab').addEventListener('click', loadAccounts);
    document.getElementById('transactions-tab').addEventListener('click', loadTransactions);
    document.getElementById('users-tab').addEventListener('click', loadUsers);

    // Logout button event
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Save buttons for modals
    saveAccountBtn.addEventListener('click', saveAccount);
    saveTransactionBtn.addEventListener('click', saveTransaction);
    saveUserBtn.addEventListener('click', saveUser);

    // Add transaction button
    const addTransactionBtn = document.getElementById('addTransactionBtn');
    if (addTransactionBtn) {
        addTransactionBtn.addEventListener('click', () => {
            // Set default date to today
            document.getElementById('transactionDate').valueAsDate = new Date();

            // Set default transaction type to expense
            const transactionType = document.getElementById('transactionType');
            transactionType.value = 'expense';

            // Load accounts first, then update the form
            debugAndPopulateAccounts(); // Use the new direct debugging function
        });
    }

    // Add event listener for transaction modal shown event
    const addTransactionModal = document.getElementById('addTransactionModal');
    if (addTransactionModal) {
        addTransactionModal.addEventListener('shown.bs.modal', function() {
            console.log("Transaction modal shown, populating accounts");
            debugAndPopulateAccounts();
        });
    }

    // Transaction type change
    const transactionType = document.getElementById('transactionType');
    if (transactionType) {
        transactionType.addEventListener('change', handleTransactionTypeChange);
    }
});

// API request function with authentication
async function apiRequest(endpoint, method = 'GET', data = null) {
    try {
        // Don't add the /api prefix - the endpoints are already at the root
        const url = endpoint.startsWith('http') ? endpoint : endpoint;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        // Add token if available
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }

        // Add body for non-GET requests
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        console.log(`Making ${method} request to ${url}`, options);
        const response = await fetch(url, options);

        // Special debug for accounts endpoint
        if (endpoint === '/accounts/') {
            console.log('Accounts endpoint response status:', response.status);
            console.log('Accounts endpoint response headers:', [...response.headers.entries()]);
        }

        // Handle 401 Unauthorized
        if (response.status === 401) {
            console.error('Authentication failed. Redirecting to login.');
            token = '';
            localStorage.removeItem('token');
            showLoginForm();
            return null;
        }

        // Handle other errors
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `Error: ${response.status} ${response.statusText}`;
            showToast(errorMessage, 'error');
            console.error('API Error:', errorMessage);
            return null;
        }

        // Parse and return response data
        const responseData = await response.json();
        console.log('API Response:', responseData);
        return responseData;
    } catch (error) {
        console.error('API Request failed:', error);
        showToast('Failed to connect to the server. Please try again.', 'error');
        return null;
    }
}

// Authentication Functions
async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        console.log('Attempting login with username:', username);
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        console.log('Login response status:', response.status);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Login error details:', errorData);
            showToast('Login failed: ' + (errorData.detail || 'Check your credentials'), 'error');
            return;
        }

        const data = await response.json();
        console.log('Login successful, token received');

        // Save token
        token = data.access_token;
        localStorage.setItem('token', token);

        // Show dashboard
        showDashboard();
        showToast('Login successful!', 'success');

        // Load initial data
        loadAccounts();
    } catch (error) {
        console.error('Login failed:', error);
        showToast('Failed to connect to the server. Please try again.', 'error');
    }
}

async function handleLogout() {
    try {
        // Call the logout endpoint
        await apiRequest('/auth/logout', 'POST');

        // Clear token from localStorage
        localStorage.removeItem('token');
        token = '';

        // Redirect to login page
        window.location.reload();
        showToast('Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
        // Even if the server request fails, we should still log out locally
        localStorage.removeItem('token');
        token = '';
        window.location.reload();
    }
}

function showDashboard() {
    loginForm.closest('.card').style.display = 'none';
    dashboard.style.display = 'block';
    loadAccounts();
}

function showLoginForm() {
    dashboard.style.display = 'none';
    loginForm.closest('.card').style.display = 'block';
}

// Account Functions
async function loadAccounts() {
    console.log('Starting to load accounts...');
    accountsTable.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';

    console.log('Making API request to /accounts/');
    const accounts = await apiRequest('/accounts/');
    console.log('API response for accounts:', accounts);

    if (accounts) {
        console.log(`Found ${accounts.length} accounts, updating table`);
        accountsTable.innerHTML = '';

        accounts.forEach(account => {
            const row = document.createElement('tr');

            const balanceClass = parseFloat(account.balance) >= 0 ? 'balance-positive' : 'balance-negative';

            row.innerHTML = `
                <td>${account.id}</td>
                <td>${account.name}</td>
                <td>${account.account_type}</td>
                <td>${account.description || '-'}</td>
                <td class="${balanceClass}">${formatCurrency(account.balance)}</td>
                <td>
                    <button class="btn btn-sm btn-info view-account" data-id="${account.id}">View</button>
                    <button class="btn btn-sm btn-danger delete-account" data-id="${account.id}">Delete</button>
                </td>
            `;

            accountsTable.appendChild(row);
        });

        // Add event listeners to buttons
        document.querySelectorAll('.delete-account').forEach(btn => {
            btn.addEventListener('click', (e) => deleteAccount(e.target.dataset.id));
        });

        // Also update account selects in transaction modal
        updateAccountSelects();
    } else {
        console.error('Failed to load accounts or received empty accounts list');
        accountsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load accounts. Please check your connection and try again.</td></tr>';
    }
}

async function saveAccount() {
    const name = document.getElementById('accountName').value;
    const account_type = document.getElementById('accountType').value;
    const description = document.getElementById('accountDescription').value;

    // Basic validation
    if (!name || !account_type) {
        showToast('Please fill in all required fields.', 'error');
        return;
    }

    const accountData = {
        name,
        account_type,
        description
    };

    console.log('Saving new account:', accountData);
    const result = await apiRequest('/accounts/', 'POST', accountData);

    if (result) {
        showToast('Account created successfully!', 'success');
        
        // Reload accounts in all places
        loadAccounts();
        
        // Also directly populate account selects for transaction form
        debugAndPopulateAccounts();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
        modal.hide();
        document.getElementById('addAccountForm').reset();
    } else {
        showToast('Failed to create account. Please try again.', 'error');
    }
}

async function deleteAccount(id) {
    if (confirm('Are you sure you want to delete this account? This cannot be undone.')) {
        const result = await apiRequest(`/accounts/${id}`, 'DELETE');

        if (result) {
            showToast('Account deleted successfully!', 'success');
            loadAccounts();
        }
    }
}

// Transaction Functions
async function loadTransactions() {
    transactionsTable.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';

    const transactions = await apiRequest('/transactions/');

    if (transactions) {
        transactionsTable.innerHTML = '';

        transactions.forEach(transaction => {
            const row = document.createElement('tr');

            // Calculate total amount (sum of all debits or credits)
            const totalAmount = transaction.entries.reduce((sum, entry) => sum + entry.debit_amount, 0);

            row.innerHTML = `
                <td>${transaction.id}</td>
                <td>${transaction.reference_number}</td>
                <td>${transaction.description || '-'}</td>
                <td>${formatDate(transaction.transaction_date)}</td>
                <td>${formatCurrency(totalAmount)}</td>
                <td>
                    <button class="btn btn-sm btn-info view-transaction" data-id="${transaction.id}">View</button>
                    <button class="btn btn-sm btn-danger delete-transaction" data-id="${transaction.id}">Delete</button>
                </td>
            `;

            transactionsTable.appendChild(row);
        });

        // Add event listeners to buttons
        document.querySelectorAll('.delete-transaction').forEach(btn => {
            btn.addEventListener('click', (e) => deleteTransaction(e.target.dataset.id));
        });
    }
}

// Handle transaction type change
function handleTransactionTypeChange() {
    console.log("Transaction type changed");
    const transactionType = document.getElementById('transactionType').value;
    const mainAccountLabel = document.getElementById('mainAccountLabel');
    const counterAccountLabel = document.getElementById('counterAccountLabel');

    console.log(`Changing labels for transaction type: ${transactionType}`);

    // Update labels based on transaction type
    if (transactionType === 'expense') {
        mainAccountLabel.textContent = 'Pay From (Your Account)';
        counterAccountLabel.textContent = 'Pay To (Expense Category)';
    } else if (transactionType === 'income') {
        mainAccountLabel.textContent = 'Receive To (Your Account)';
        counterAccountLabel.textContent = 'Receive From (Income Source)';
    } else if (transactionType === 'transfer') {
        mainAccountLabel.textContent = 'From Account';
        counterAccountLabel.textContent = 'To Account';
    }

    // Repopulate accounts first to ensure we have all accounts loaded
    debugAndPopulateAccounts();
}

function updateCounterAccountOptions(transactionType) {
    console.log(`Updating counter account options for transaction type: ${transactionType}`);
    const counterAccountSelect = document.getElementById('counterAccount');

    if (!counterAccountSelect) {
        console.error("Counter account select element not found");
        return;
    }

    // Get all options from the main account select
    const accounts = Array.from(document.querySelectorAll('#mainAccount option')).slice(1);
    console.log(`Found ${accounts.length} accounts in main select for filtering`);

    // Clear existing options except the first one
    while (counterAccountSelect.options.length > 1) {
        counterAccountSelect.remove(1);
    }

    // Filter accounts based on transaction type
    let filteredAccounts = accounts;

    if (transactionType === 'expense') {
        // For expenses, counter account should be expense accounts
        console.log("Filtering for expense accounts");
        filteredAccounts = accounts.filter(opt =>
            opt.dataset.type === 'expense');
    } else if (transactionType === 'income') {
        // For income, counter account should be revenue accounts
        console.log("Filtering for revenue accounts");
        filteredAccounts = accounts.filter(opt =>
            opt.dataset.type === 'revenue');
    }

    console.log(`After filtering, found ${filteredAccounts.length} accounts for counter select`);

    // Add filtered options to counter account select
    filteredAccounts.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.textContent;
        option.dataset.type = opt.dataset.type;
        counterAccountSelect.appendChild(option);
    });

    // If no accounts were filtered, add a message
    if (filteredAccounts.length === 0) {
        const option = document.createElement('option');
        option.value = "";
        option.textContent = `No ${transactionType === 'expense' ? 'expense' : 'revenue'} accounts available - create one first`;
        counterAccountSelect.appendChild(option);
        console.log(`No ${transactionType} accounts found, added placeholder option`);
    }
}

// Save transaction
async function saveTransaction() {
    const reference_number = document.getElementById('transactionReference').value;
    const description = document.getElementById('transactionDescription').value;
    const transaction_date = document.getElementById('transactionDate').value;
    const transactionType = document.getElementById('transactionType').value;

    const mainAccountId = document.getElementById('mainAccount').value;
    const counterAccountId = document.getElementById('counterAccount').value;
    const amount = parseFloat(document.getElementById('transactionAmount').value);

    // Basic validation
    if (!reference_number || !transaction_date || !mainAccountId || !counterAccountId || isNaN(amount) || amount <= 0) {
        showToast('Please fill in all fields with valid values.', 'error');
        return;
    }

    let entries = [];

    // Create entries based on transaction type
    switch (transactionType) {
        case 'expense':
            // Debit expense account, credit asset account
            entries = [
                {
                    account_id: parseInt(counterAccountId),
                    debit_amount: amount,
                    credit_amount: 0,
                    description: description
                },
                {
                    account_id: parseInt(mainAccountId),
                    debit_amount: 0,
                    credit_amount: amount,
                    description: description
                }
            ];
            break;

        case 'income':
            // Debit asset account, credit revenue account
            entries = [
                {
                    account_id: parseInt(mainAccountId),
                    debit_amount: amount,
                    credit_amount: 0,
                    description: description
                },
                {
                    account_id: parseInt(counterAccountId),
                    debit_amount: 0,
                    credit_amount: amount,
                    description: description
                }
            ];
            break;

        case 'transfer':
            // Transfer between accounts
            entries = [
                {
                    account_id: parseInt(counterAccountId),
                    debit_amount: amount,
                    credit_amount: 0,
                    description: description
                },
                {
                    account_id: parseInt(mainAccountId),
                    debit_amount: 0,
                    credit_amount: amount,
                    description: description
                }
            ];
            break;
    }

    const transactionData = {
        reference_number,
        description,
        transaction_date,
        entries
    };

    console.log('Sending transaction data:', transactionData);

    const result = await apiRequest('/transactions/', 'POST', transactionData);

    if (result) {
        showToast('Transaction created successfully!', 'success');
        loadTransactions();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
        modal.hide();
        document.getElementById('addTransactionForm').reset();
    }
}

async function deleteTransaction(id) {
    if (confirm('Are you sure you want to delete this transaction? This cannot be undone.')) {
        const result = await apiRequest(`/transactions/${id}`, 'DELETE');

        if (result) {
            showToast('Transaction deleted successfully!', 'success');
            loadTransactions();
        }
    }
}

// User Functions
async function loadUsers() {
    usersTable.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';

    const users = await apiRequest('/users/');

    if (users) {
        usersTable.innerHTML = '';

        users.forEach(user => {
            const row = document.createElement('tr');

            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>
                    <button class="btn btn-sm btn-info view-user" data-id="${user.id}">View</button>
                    <button class="btn btn-sm btn-danger delete-user" data-id="${user.id}">Delete</button>
                </td>
            `;

            usersTable.appendChild(row);
        });

        // Add event listeners to buttons
        document.querySelectorAll('.delete-user').forEach(btn => {
            btn.addEventListener('click', (e) => deleteUser(e.target.dataset.id));
        });
    }
}

async function saveUser() {
    const username = document.getElementById('userName').value;
    const email = document.getElementById('userEmail').value;
    const password = document.getElementById('userPassword').value;

    const userData = {
        username,
        email,
        password
    };

    const result = await apiRequest('/users/', 'POST', userData);

    if (result) {
        showToast('User created successfully!', 'success');
        loadUsers();

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
        modal.hide();
        document.getElementById('addUserForm').reset();
    }
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');

    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    // Create toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Add toast to container
    toastContainer.appendChild(toast);

    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });

    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

function updateAccountSelects() {
    return new Promise((resolve, reject) => {
        // Get all accounts
        console.log("Fetching accounts...");
        apiRequest('/accounts/').then(accounts => {
            console.log("Accounts received:", accounts);
            if (!accounts) {
                console.error("No accounts received");
                showToast('Failed to load accounts. Please check your connection.', 'error');
                return reject();
            }

            // Update all account selects in the transaction form
            const mainAccountSelect = document.getElementById('mainAccount');
            const counterAccountSelect = document.getElementById('counterAccount');

            console.log("Main account select:", mainAccountSelect);
            console.log("Counter account select:", counterAccountSelect);

            if (!mainAccountSelect || !counterAccountSelect) {
                console.error("Account select elements not found in the DOM");
                return reject();
            }

            // Clear existing options except the first one
            if (mainAccountSelect) {
                while (mainAccountSelect.options.length > 1) {
                    mainAccountSelect.remove(1);
                }
            }

            if (counterAccountSelect) {
                while (counterAccountSelect.options.length > 1) {
                    counterAccountSelect.remove(1);
                }
            }

            // Add account options
            if (accounts && Array.isArray(accounts) && accounts.length > 0) {
                accounts.forEach(account => {
                    console.log("Adding account:", account);

                    // Create option for main account select
                    if (mainAccountSelect) {
                        const mainOption = document.createElement('option');
                        mainOption.value = account.id;
                        mainOption.textContent = `${account.name} (${account.account_type})`;
                        mainOption.dataset.type = account.account_type;
                        mainAccountSelect.appendChild(mainOption);
                    }

                    // Create separate option for counter account select
                    if (counterAccountSelect) {
                        const counterOption = document.createElement('option');
                        counterOption.value = account.id;
                        counterOption.textContent = `${account.name} (${account.account_type})`;
                        counterOption.dataset.type = account.account_type;
                        counterAccountSelect.appendChild(counterOption);
                    }
                });

                // If transaction type is set, update counter account options
                const transactionType = document.getElementById('transactionType');
                if (transactionType && transactionType.value) {
                    updateCounterAccountOptions(transactionType.value);
                }

                console.log("Account options updated");
                resolve();
            } else {
                console.error("No accounts available or accounts not in expected format:", accounts);
                showToast('No accounts available. Please create an account first.', 'warning');

                // Add a default option to show there are no accounts
                if (mainAccountSelect) {
                    const option = document.createElement('option');
                    option.value = "";
                    option.textContent = "No accounts available - create an account first";
                    mainAccountSelect.appendChild(option);
                }

                if (counterAccountSelect) {
                    const option = document.createElement('option');
                    option.value = "";
                    option.textContent = "No accounts available - create an account first";
                    counterAccountSelect.appendChild(option);
                }

                resolve();
            }
        }).catch(error => {
            console.error("Error fetching accounts:", error);
            showToast('Error loading accounts. Please try again.', 'error');
            reject(error);
        });
    });
}

// Add this function to directly debug and populate account selects
function debugAndPopulateAccounts() {
    console.log("Starting direct account debug and population");

    // Make a direct fetch call to the accounts endpoint
    fetch('/accounts/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        console.log("Direct accounts fetch response status:", response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(accounts => {
        console.log("Direct accounts fetch result:", accounts);

        // Get the select elements
        const mainAccountSelect = document.getElementById('mainAccount');
        const counterAccountSelect = document.getElementById('counterAccount');

        if (!mainAccountSelect || !counterAccountSelect) {
            console.error("Could not find account select elements");
            return;
        }

        // Clear existing options except the first one
        while (mainAccountSelect.options.length > 1) {
            mainAccountSelect.remove(1);
        }

        while (counterAccountSelect.options.length > 1) {
            counterAccountSelect.remove(1);
        }

        // Check if accounts is an array and has items
        if (!Array.isArray(accounts) || accounts.length === 0) {
            console.error("No accounts found or accounts is not an array:", accounts);

            // Add placeholder options
            const noAccountsOption = document.createElement('option');
            noAccountsOption.value = "";
            noAccountsOption.textContent = "No accounts available - create an account first";

            mainAccountSelect.appendChild(noAccountsOption.cloneNode(true));
            counterAccountSelect.appendChild(noAccountsOption.cloneNode(true));

            return;
        }

        // Add accounts to both selects
        accounts.forEach(account => {
            // Create option for main account
            const mainOption = document.createElement('option');
            mainOption.value = account.id;
            mainOption.textContent = `${account.name} (${account.account_type})`;
            mainOption.dataset.type = account.account_type;
            mainAccountSelect.appendChild(mainOption);

            // Create option for counter account
            const counterOption = document.createElement('option');
            counterOption.value = account.id;
            counterOption.textContent = `${account.name} (${account.account_type})`;
            counterOption.dataset.type = account.account_type;
            counterAccountSelect.appendChild(counterOption);
        });

        console.log("Account selects populated directly");

        // Update counter account options based on transaction type
        const transactionType = document.getElementById('transactionType');
        if (transactionType) {
            updateCounterAccountOptions(transactionType.value);
        }
    })
    .catch(error => {
        console.error("Error in direct account fetch:", error);
    });
}
