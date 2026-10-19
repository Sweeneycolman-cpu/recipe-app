import hashlib
import hmac
import json
import uuid
import streamlit as st
from core import Store, match, normalise

st.set_page_config(page_title='Our Recipe Book', page_icon='🍋', layout='centered', initial_sidebar_state='collapsed')
st.markdown('''<style>
.stApp {background:#faf8f2} .block-container {max-width:740px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {color:#294c3b} .stButton button,.stDownloadButton button {min-height:48px;border-radius:12px}
[data-baseweb="input"],[data-baseweb="select"] {font-size:16px} textarea {font-size:16px!important}
</style>''', unsafe_allow_html=True)
try:
    settings = dict(st.secrets)
except FileNotFoundError:
    settings = {}
except st.errors.StreamlitSecretNotFoundError:
    settings = {}
cloud = bool(settings.get('supabase_url') and settings.get('supabase_service_key'))
password_hash = settings.get('password_sha256')
if cloud and not password_hash:
    st.error('Please finish setting up the recipe book password before using cloud storage.')
    st.stop()
if password_hash and not st.session_state.get('unlocked'):
    st.title('🍋 Our Recipe Book')
    st.write('Your meals, all in one place.')
    with st.form('unlock'):
        password = st.text_input('Password', type='password')
        if st.form_submit_button('Open recipe book', type='primary', use_container_width=True):
            if hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), password_hash):
                st.session_state.unlocked = True
                st.rerun()
            else:
                st.error('That password didn’t match. Please try again.')
    st.stop()
store = Store(settings)
if not cloud:
    st.info('Preview mode · Recipes save on this computer. Connect cloud storage before publishing.')
if notice := st.session_state.pop('notice', None):
    st.success(notice)
st.title('🍋 Our Recipe Book')
st.caption('A little inspiration for what’s for dinner.')
try:
    recipes = store.all()
except Exception:
    st.error('We couldn’t open your recipes. Please check your connection and try again.')
    if st.button('Try again'): st.rerun()
    st.stop()
page = st.radio('Go to', ['Find a meal', 'Add a meal', 'My recipe book'], horizontal=True, label_visibility='collapsed')
editing = st.session_state.get('editing')
if editing or page == 'Add a meal':
    st.subheader('Edit meal' if editing else 'Add something delicious')
    st.caption('Start with a name and ingredients. Everything else is optional.')
    recipe = editing or {}
    form_id = recipe.get('id', 'new') + str(st.session_state.get('form_version', 0))
    with st.form('meal_' + form_id):
        name = st.text_input('Meal name', value=recipe.get('name', ''), placeholder='e.g. Chicken & pepper rice')
        st.write('**Ingredients**')
        st.caption('One ingredient per row. Put amounts in the second column, e.g. chicken | 300 g. Tap a blank row to add more.')
        rows = st.data_editor(recipe.get('ingredients') or [{'name': '', 'quantity': ''}], num_rows='dynamic', hide_index=True, use_container_width=True, column_config={'name': st.column_config.TextColumn('Ingredient', required=True), 'quantity': st.column_config.TextColumn('Amount (optional)')}, key='ingredients_' + form_id)
        servings = st.number_input('Serves', min_value=1, max_value=100, value=recipe.get('servings', 2))
        instructions = st.text_area('How to make it (optional)', value=recipe.get('instructions', ''), placeholder='Write each step on a new line.', height=160)
        submitted = st.form_submit_button('Save meal', type='primary', use_container_width=True)
    if submitted:
        ingredients = []
        seen = set()
        for row in rows:
            ingredient = normalise(row.get('name') or '')
            if ingredient and ingredient not in seen:
                ingredients.append({'name': ingredient, 'quantity': (row.get('quantity') or '').strip()})
                seen.add(ingredient)
        duplicate = any(normalise(r['name']) == normalise(name) and r['id'] != recipe.get('id') for r in recipes)
        if not name.strip(): st.error('Give your meal a name before saving.')
        elif not ingredients: st.error('Add at least one ingredient before saving.')
        elif duplicate: st.error('You already have a meal with that name. Choose another name or edit the existing meal.')
        else:
            try:
                store.save({'id': recipe.get('id', str(uuid.uuid4())), 'name': name.strip(), 'ingredients': ingredients, 'servings': int(servings), 'instructions': instructions.strip()}, bool(editing))
                st.session_state.pop('editing', None)
                st.session_state.form_version = st.session_state.get('form_version', 0) + 1
                st.session_state.notice = 'Meal saved! Find it in your recipe book.'
                st.rerun()
            except Exception:
                st.error('Your meal couldn’t be saved. Your entries are still here—please try again.')
    if editing and st.button('Cancel editing'):
        st.session_state.pop('editing', None)
        st.rerun()
else:
    query = st.text_input('Find a meal by name', placeholder='e.g. curry')
    selected, pantry, only = [], [], False
    if page == 'Find a meal':
        options = sorted({i['name'] for r in recipes for i in r['ingredients']})
        selected = st.multiselect('Which ingredients would you like to use?', options, placeholder='Choose ingredients…')
        only = st.toggle('Only what I have', help='Show meals needing only your selected ingredients and pantry basics.')
        if only:
            pantry = st.multiselect('Pantry basics you already have', sorted(set(options) | {'salt', 'pepper', 'oil', 'water'}), default=['salt', 'pepper', 'oil', 'water'])
            st.caption('Select everything you have available, including pantry basics.')
        else:
            st.caption('Meals must contain every ingredient you select. Other ingredients are allowed.')
    results = match(recipes, query, selected, only, pantry)
    if not recipes:
        st.write('### Your recipe book starts here')
        st.write('Tap **Add a meal** above to save your first favourite. Once you’ve added a few, you can search by ingredients.')
    elif not results:
        st.info('No meals match yet. Try removing an ingredient or switching off “Only what I have”.')
    else:
        st.caption(f'{len(results)} meal' + ('s' if len(results) != 1 else '') + ' found')
        for recipe, missing in results:
            with st.expander(recipe['name']):
                st.caption(f"Serves {recipe['servings']}")
                if selected:
                    st.write('✅ Ready to cook' if not missing else 'Also needed: ' + ', '.join(missing))
                st.write('**Ingredients**')
                for ingredient in recipe['ingredients']:
                    st.text(' • ' + ingredient['name'].capitalize() + (' — ' + ingredient['quantity'] if ingredient['quantity'] else ''))
                if recipe.get('instructions'):
                    st.write('**Method**')
                    for step in recipe['instructions'].splitlines():
                        if step.strip(): st.text(step.strip())
                if st.button('Edit meal', key='edit_' + recipe['id'], use_container_width=True):
                    st.session_state.editing = recipe
                    st.rerun()
                with st.popover('Delete meal'):
                    st.write('Permanently delete ' + recipe['name'] + '?')
                    if st.button('Yes, delete meal', key='delete_' + recipe['id']):
                        try:
                            store.delete(recipe['id'])
                            st.session_state.notice = 'Meal deleted.'
                            st.rerun()
                        except Exception:
                            st.error('Couldn’t delete the meal. Please try again.')
    if recipes and page == 'My recipe book':
        st.download_button('Download a backup', json.dumps(recipes, indent=2), file_name='my-recipes.json', mime='application/json', use_container_width=True)
