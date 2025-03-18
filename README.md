# Accounting Backend System

A robust backend system for accounting with double-entry bookkeeping, built with FastAPI and PostgreSQL.

## Features

- **Double-Entry Bookkeeping**: Ensures financial data integrity with balanced transactions
- **RESTful API**: Complete CRUD operations for accounts, transactions, and users
- **Authentication**: Secure JWT token-based authentication
- **PostgreSQL Database**: Reliable and scalable data storage
- **Input Validation**: Comprehensive data validation using Pydantic
- **Clean Architecture**: Organized codebase with separation of concerns

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: Bcrypt
- **Frontend**: Bootstrap, JavaScript

## Deployment

### Railway Deployment

This project is configured for deployment on Railway with the following files:

- `railway.json`: Configuration for Railway deployment
- `Dockerfile`: Container configuration for the application
- `Procfile`: Alternative deployment method using Procfile

#### Required Environment Variables

When deploying to Railway, set the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string (automatically set by Railway when adding a PostgreSQL plugin)
- `SECRET_KEY`: A secure random string for JWT token generation
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (e.g., "https://yourdomain.com,http://localhost:3000")
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30)

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up PostgreSQL database
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
