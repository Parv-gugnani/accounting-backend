# Accounting Backend System

A robust backend system for accounting with double-entry bookkeeping, built with FastAPI and PostgreSQL/Supabase.

## Features

- **Double-Entry Bookkeeping**: Ensures financial data integrity with balanced transactions
- **RESTful API**: Complete CRUD operations for accounts, transactions, and users
- **Authentication**: Secure JWT token-based authentication
- **Database**: PostgreSQL (with ongoing migration to Supabase)
- **Input Validation**: Comprehensive data validation using Pydantic
- **Clean Architecture**: Organized codebase with separation of concerns
- **User-Friendly Frontend**: HTML/JavaScript interface for managing accounts and transactions

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (migrating to Supabase)
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: Bcrypt
- **Frontend**: Bootstrap, JavaScript, HTML

## Frontend Implementation

The application includes a complete frontend implementation:
- HTML templates served from `/app/templates`
- Static files (JS, CSS, images) served from `/app/static`
- Responsive design using Bootstrap
- Client-side JavaScript for dynamic interactions

### Demo

To see the application in action, check out the [Screen Recording](https://github.com/Parv-gugnani/accounting-backend/blob/main/Screen%20Recording%202025-03-20%20at%204.33.34%20PM.mov) in the repository.

## Recent Updates

- **Account Loading Fix**: Improved account loading in transaction forms with direct API calls and better error handling
- **Enhanced Debugging**: Added detailed logging for API responses to facilitate troubleshooting
- **Supabase Migration**: Ongoing migration from PostgreSQL to Supabase for improved scalability

## Deployment

### Railway Deployment

This project is configured for deployment on Railway with the following files:

- `railway.json`: Configuration for Railway deployment
- `Dockerfile`: Container configuration for the application
- `Procfile`: Alternative deployment method using Procfile

#### Required Environment Variables

When deploying to Railway, set the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string (automatically set by Railway when adding a PostgreSQL plugin)
- `SUPABASE_URL`: Supabase project URL (if using Supabase)
- `SECRET_KEY`: A secure random string for JWT token generation
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (e.g., "https://yourdomain.com,http://localhost:3000")
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30)

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up PostgreSQL database or Supabase connection
4. Update database connection in `app/db/database.py` if needed
5. Run the application:
   ```
   uvicorn app.main:app --reload --port 8090
   ```

## API Endpoints

### Authentication
- `POST /auth/token`: Login and get access token
- `POST /auth/logout`: Logout (client-side token removal)

### Users
- `POST /users/`: Create a new user
- `GET /users/me`: Get current user information
- `GET /users/{user_id}`: Get specific user information

### Accounts
- `GET /accounts/`: List all accounts
- `POST /accounts/`: Create a new account
- `GET /accounts/{account_id}`: Get account details
- `DELETE /accounts/{account_id}`: Delete an account

### Transactions
- `GET /transactions/`: List all transactions
- `POST /transactions/`: Create a new transaction
- `GET /transactions/{transaction_id}`: Get transaction details
- `DELETE /transactions/{transaction_id}`: Delete a transaction

## Database Schema

The system uses the following main tables:

- **Users**: Store user information and authentication details
- **Accounts**: Chart of accounts with different account types
- **Transactions**: Header information for financial transactions
- **TransactionEntries**: Individual debit/credit entries for double-entry bookkeeping

## License

MIT
