### Ticket Title
Build interface for FPL user lookup and team retrieval

---

### Description
We want to extend the current FPL project to allow users to look up their team and view its players.  
The user can enter either their **team name** or **manager name**, and the system will search the production database to find their manager details.  
If the system cannot find a match, the user will be prompted to manually provide their `manager_id`.  
Once the `manager_id` is obtained, we will query the FPL API to retrieve their team and display it in a simple list format.

---

### Requirements
1. **User Input Flow**
   - User enters **team name** or **manager name**.
   - System queries the `all_managers` table in the **production database** for a matching row.
     ```sql
     SELECT * FROM all_managers
     WHERE manager_name ILIKE %input%
        OR team_name ILIKE %input%;
     ```
   - If no match is found, prompt the user for their `manager_id`.

2. **API Integration**
   - Once the `manager_id` is known, send a GET request to:
     ```
     https://fantasy.premierleague.com/api/my-team/{manager_id}/
     ```
   - Parse the JSON response and extract the user’s team data.
   - For now, simply **list the team** in a clean text or table format (no extra styling or components yet).

3. **Implementation Guidelines**
   - Keep the code **DRY**, concise, and under **100 lines per file**.
   - Minimal dependencies — prefer the standard library and lightweight HTTP/database clients.
   - Environment variable or config-based DB connection (always use **production DB** for this feature).
   - Organize code into logical modules (e.g. `db.py`, `api.py`, `main.py`).
   - Use async/await where possible for efficient IO.

4. **Error Handling**
   - If no manager is found → ask for `manager_id`.
   - If API request fails → log and show user-friendly message.
   - Handle invalid JSON or missing fields gracefully.

---

### Acceptance Criteria
- User can search for their manager by team name or manager name.
- If not found, they are prompted to provide a `manager_id`.
- Once a `manager_id` is known, their team is fetched from the FPL API and displayed as a list.
- Code remains minimal, modular, and well-structured (<100 lines per file).
- Database query and API request work correctly against the **production** environment.

---

### Stretch Goal (Optional)
- Add a caching layer or small SQLite mirror to reduce API calls.
- Extend the output to include captain, vice-captain, and formation details.
