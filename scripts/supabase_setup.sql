-- SQL script to set up tables in Supabase
-- Run this in the Supabase SQL Editor

-- Create users table
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username_email ON public.users (username, email);

-- Create accounts table
CREATE TABLE IF NOT EXISTS public.accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_valid_account_type CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense'))
);

CREATE INDEX IF NOT EXISTS ix_accounts_owner_id_name ON public.accounts (owner_id, name);
CREATE INDEX IF NOT EXISTS ix_accounts_account_type ON public.accounts (account_type);

-- Create transactions table
CREATE TABLE IF NOT EXISTS public.transactions (
    id SERIAL PRIMARY KEY,
    reference_number VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_transactions_transaction_date ON public.transactions (transaction_date);
CREATE INDEX IF NOT EXISTS ix_transactions_created_by_id ON public.transactions (created_by_id);

-- Create transaction_entries table
CREATE TABLE IF NOT EXISTS public.transaction_entries (
    id SERIAL PRIMARY KEY,
    debit_amount FLOAT NOT NULL DEFAULT 0.0,
    credit_amount FLOAT NOT NULL DEFAULT 0.0,
    description TEXT,
    transaction_id INTEGER NOT NULL REFERENCES public.transactions(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES public.accounts(id),
    CONSTRAINT check_debit_xor_credit CHECK 
        ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
);

CREATE INDEX IF NOT EXISTS ix_transaction_entries_transaction_id ON public.transaction_entries (transaction_id);
CREATE INDEX IF NOT EXISTS ix_transaction_entries_account_id ON public.transaction_entries (account_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transaction_entries ENABLE ROW LEVEL SECURITY;

-- Create policies for users table
CREATE POLICY "Users can view their own data" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own data" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Create policies for accounts table
CREATE POLICY "Users can view their own accounts" ON public.accounts
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Users can insert their own accounts" ON public.accounts
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Users can update their own accounts" ON public.accounts
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "Users can delete their own accounts" ON public.accounts
    FOR DELETE USING (auth.uid() = owner_id);

-- Create policies for transactions table
CREATE POLICY "Users can view their own transactions" ON public.transactions
    FOR SELECT USING (auth.uid() = created_by_id);

CREATE POLICY "Users can insert their own transactions" ON public.transactions
    FOR INSERT WITH CHECK (auth.uid() = created_by_id);

CREATE POLICY "Users can update their own transactions" ON public.transactions
    FOR UPDATE USING (auth.uid() = created_by_id);

CREATE POLICY "Users can delete their own transactions" ON public.transactions
    FOR DELETE USING (auth.uid() = created_by_id);

-- Create policies for transaction_entries table
CREATE POLICY "Users can view entries for their transactions" ON public.transaction_entries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.transactions t
            WHERE t.id = transaction_id AND t.created_by_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert entries for their transactions" ON public.transaction_entries
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.transactions t
            WHERE t.id = transaction_id AND t.created_by_id = auth.uid()
        )
    );

CREATE POLICY "Users can update entries for their transactions" ON public.transaction_entries
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.transactions t
            WHERE t.id = transaction_id AND t.created_by_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete entries for their transactions" ON public.transaction_entries
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.transactions t
            WHERE t.id = transaction_id AND t.created_by_id = auth.uid()
        )
    );
