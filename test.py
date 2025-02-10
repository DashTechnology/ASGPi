#!/usr/bin/env python3
"""
Driver script for fetching real data using DatabaseManager.get_positions.

This script connects to the Supabase database using credentials from environment
variables and prints the positions data retrieved from the asg_positions table.
Make sure SUPABASE_URL and SUPABASE_KEY environment variables are configured properly.
"""

import json
from database_manager import DatabaseManager


def main() -> None:
    """
    The main function that retrieves and prints real data from the database.
    """
    try:
        # Instantiate DatabaseManager, which loads the environment variables and initializes Supabase client
        db_manager: DatabaseManager = DatabaseManager()

        # Retrieve all positions from the database
        positions: list[dict[str, object]] = db_manager.get_positions()

        # Print the retrieved data in a formatted JSON structure
        print("Real data from database:")
        print(json.dumps(positions, indent=4))
    except Exception as error:
        # Print error message if an exception occurs
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
