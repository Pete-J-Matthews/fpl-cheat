### Ticket Title
Fetch and store limited FPL manager data from the FPL API with environment-based database selection

---

### Description
We want to retrieve **only three specific fields** from the Fantasy Premier League (FPL) API and insert them into a database table.  
The script should accept a command-line argument (`local` or `production`) to determine which database connection to use.

The API endpoint for the league standings is:

https://fantasy.premierleague.com/api/leagues-classic/314/standings/


The number `314` represents the **overall league**, which includes all managers.  
The endpoint is **paginated**, so the script must handle pagination to retrieve all records.

---

### Requirements
1. **Fetch data** from the API (handle pagination).  
   Example response structure:
   ```json
   {
     "standings": {
       "results": [
         {
           "id": 12345,
           "player_name": "John Smith",
           "entry_name": "Smith United"
         }
       ]
     }
   }

    Extract only these fields:

        id → manager_id

        player_name → manager_name

        entry_name → team_name

    Insert data into a table:

CREATE TABLE IF NOT EXISTS fpl_managers (
    manager_id INT PRIMARY KEY,
    manager_name TEXT,
    team_name TEXT
);

Environment-based database connection:

    The script must accept one argument: local or production.

    Depending on the argument, it will use the corresponding database credentials, e.g.:

        if env == "local":
            db_url = "postgresql://user:password@localhost:5432/local_db"
        elif env == "production":
            db_url = "postgresql://user:password@prod-host:5432/prod_db"
        else:
            raise ValueError("Environment must be 'local' or 'production'")

    Handle pagination using the standings pagination fields (has_next, page, etc.), looping until all pages are retrieved.

    Error handling:

        Retry failed API calls up to 3 times with exponential backoff.

        Log skipped records or API errors without stopping the whole process.

    Insert behavior:

        If a manager_id already exists, ignore or update the existing row.

        Prevent duplicate insertions when rerunning the command.

Acceptance Criteria

    The script successfully fetches and stores only manager_id, manager_name, and team_name.

    The local or production argument correctly determines which database is used.

    Pagination ensures all pages of the overall league (ID 314) are retrieved.

    No duplicates are inserted.

    Console logs clearly show progress and the selected environment (e.g. “Using local DB”, “Fetched page 2 of 45”, “Inserted 50 managers”).