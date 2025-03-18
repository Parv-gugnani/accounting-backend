# Accounting System Backend

A robust accounting backend system built with FastAPI and PostgreSQL, implementing double-entry bookkeeping principles.

## Features

- **User Management**: Create and authenticate users
- **Account Management**: Create, read, update, and delete financial accounts
- **Transaction Management**: Record financial transactions with double-entry bookkeeping
- **RESTful API**: Well-structured API endpoints for all operations
- **Data Validation**: Input validation and error handling
- **Database Integrity**: Foreign keys, constraints, and indexes for data integrity
- **Authentication**: JWT-based authentication for secure access
- **Clean Code**: Modular structure with separation of concerns
- **UI Interface**: Simple web interface for interacting with the API

## Technology Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **Validation**: Pydantic
- **Testing**: Pytest

## Project Structure

```
accounting-backend/
├── app/
│   ├── api/                 # API endpoints
│   │   ├── accounts.py      # Account endpoints
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── transactions.py  # Transaction endpoints
│   │   └── users.py         # User endpoints
│   ├── core/                # Core functionality
│   │   └── auth.py          # Authentication logic
│   ├── db/                  # Database configuration
│   │   └── database.py      # Database connection
│   ├── models/              # Database models
│   │   └── models.py        # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   │   └── schemas.py       # Request/response schemas
│   ├── static/              # Static files
│   │   ├── css/             # CSS files
│   │   └── js/              # JavaScript files
│   ├── templates/           # HTML templates
│   │   └── index.html       # Main UI template
│   ├── tests/               # Test files
│   │   └── test_accounts.py # Account tests
│   └── main.py              # Application entry point
└── README.md                # Project documentation
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/accounting-backend.git
   cd accounting-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a PostgreSQL database:
   ```bash
   createdb accounting
   ```

5. Update the database connection string in `app/db/database.py` if needed:
   ```python
   SQLALCHEMY_DATABASE_URL = "postgresql://username:password@localhost/accounting"
   ```

### Running the Application

Start the application with Uvicorn:

```bash
uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000

## API Documentation

Once the application is running, you can access the interactive API documentation at:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Example API Calls

### Authentication

```bash
# Get JWT token
curl -X POST "http://127.0.0.1:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

### Accounts

```bash
# Create account
curl -X POST "http://127.0.0.1:8000/accounts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cash",
    "account_type": "asset",
    "description": "Cash on hand"
  }'

# Get all accounts
curl -X GET "http://127.0.0.1:8000/accounts/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get account by ID
curl -X GET "http://127.0.0.1:8000/accounts/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Transactions

```bash
# Create transaction
curl -X POST "http://127.0.0.1:8000/transactions/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_number": "INV-001",
    "description": "Sale of goods",
    "date": "2023-01-01",
    "entries": [
      {
        "account_id": 1,
        "entry_type": "debit",
        "amount": 100.00
      },
      {
        "account_id": 2,
        "entry_type": "credit",
        "amount": 100.00
      }
    ]
  }'

# Get all transactions
curl -X GET "http://127.0.0.1:8000/transactions/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Testing

Run tests using pytest:

```bash
pytest app/tests/
```

## Double-Entry Bookkeeping

This system implements double-entry bookkeeping principles:

1. Every transaction must have at least two entries
2. The sum of debits must equal the sum of credits
3. Each entry affects two accounts (debit one, credit another)

## License

MIT
