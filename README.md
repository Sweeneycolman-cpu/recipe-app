# Our Recipe Book

A separate Streamlit app designed for one person's phone. Add meals, edit ingredients and quantities, search by name, match ALL selected ingredients, or switch to recipes requiring only the selected ingredients plus pantry basics. Includes editing, confirmed deletion, and JSON backup download. No AI subscriptions or paid APIs.

## Local preview

Use Python 3.10+:

```
cd recipe-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Without secrets, this saves to a local SQLite file and displays a preview banner. Do not publish preview mode: local files on Community Cloud are not durable. There are no sample meals in the real recipe book.

## Cloud setup

1. Run `setup.sql` in the intended Supabase project's SQL editor. It creates only `recipe_book_meals`. A separate project offers stronger isolation; an existing project can also host this separate table.
2. Generate a password hash locally (password input is hidden):

```
python3 -c 'import getpass,hashlib; print(hashlib.sha256(getpass.getpass("Choose password: ").encode()).hexdigest())'
```

3. Create a separate private GitHub repository containing this folder's contents. Deploy `app.py` through your Streamlit Community Cloud account.
4. In Streamlit's Secrets settings, supply the three values from `.streamlit/secrets.example.toml`. The service-role key stays on the Python server; never put it in client code or GitHub. The app refuses cloud access without its password configured. Use a strong unique password; this simple shared-password gate is intended for this single-user app and has no persistent sign-in or brute-force rate limiter. Private hosting access controls can provide an additional boundary.
5. Test on her phone: save a meal, reload, find it by name, choose two ingredients, toggle available-ingredients mode, edit, and download a backup. Test logged out as well. Add a home-screen bookmark in her browser.

Ingredient names ignore case and extra spaces; common variants such as tomatoes/tomato are merged. Other variants remain distinct: use consistent names. Pantry selection lasts only for the current session. Recipe photos and backup import are not implemented in this version.

Cloud schema and read/write access must be verified against the selected Supabase project before publishing. Free hosting/database inactivity limits still apply.
