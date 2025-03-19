from supabase import create_client
import os
import logging

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_KEY environment variables are not set. Supabase functionality will not work.")

def get_supabase_client():
    """
    Create and return a Supabase client.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Cannot initialize Supabase client: missing environment variables")
        return None
        
    try:
        logger.info("Initializing Supabase client")
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {str(e)}")
        raise

# Initialize the Supabase client
supabase = get_supabase_client()
