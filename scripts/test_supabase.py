#!/usr/bin/env python
"""
Script to test Supabase connection for the accounting backend.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

from app.core.supabase_client import supabase, SUPABASE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def test_connection():
    """Test the connection to Supabase."""
    try:
        logger.info(f"Testing connection to Supabase at {SUPABASE_URL}")
        
        if not supabase:
            logger.error("Supabase client not initialized. Check your environment variables.")
            return False
        
        # Try to get the list of tables
        response = supabase.from_("users").select("*", count="exact").limit(1).execute()
        logger.info(f"Connection successful! Found {response.count} users.")
        
        return True
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {str(e)}")
        return False

def main():
    """Main function to test Supabase connection."""
    if test_connection():
        logger.info("Supabase connection test passed!")
    else:
        logger.error("Supabase connection test failed.")

if __name__ == "__main__":
    main()
