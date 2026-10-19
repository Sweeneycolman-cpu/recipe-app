import json
import sqlite3
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import re

def connection_diagnostic(error):
    """Return only safe status codes, never URLs, headers or response messages."""
    if isinstance(error, HTTPError):
        code = ''
        try:
            candidate = json.loads(error.read(16384)).get('code', '')
            if isinstance(candidate, str) and re.fullmatch(r'[A-Z0-9]{3,16}', candidate):
                code = ' · ' + candidate
        except (ValueError, AttributeError, OSError):
            pass
        hints = {401: 'Supabase rejected the credentials.',
                 403: 'Supabase denied access to the recipe table.',
                 404: 'The recipe endpoint or table was not found.',
                 503: 'Supabase is temporarily unavailable.'}
        return f'HTTP {error.code}{code}. ' + hints.get(error.code, 'Supabase could not complete the request.')
    if isinstance(error, (URLError, TimeoutError)):
        return 'Network connection failed. The app could not reach Supabase.'
    if isinstance(error, ValueError):
        return 'The connection URL or database response has an unexpected format.'
    return 'Unexpected connection error. Check the deployed app configuration.'

ALIASES = {'tomatoes': 'tomato', 'potatoes': 'potato', 'onions': 'onion', 'peppers': 'pepper', 'carrots': 'carrot', 'eggs': 'egg', 'chickpeas': 'chickpea', 'mushrooms': 'mushroom', 'courgettes': 'courgette', 'zucchini': 'courgette', 'bell pepper': 'pepper', 'bell peppers': 'pepper'}

def normalise(value):
    value = ' '.join(unicodedata.normalize('NFKC', value).casefold().strip().split())
    return ALIASES.get(value, value)

def match(recipes, query='', selected=(), only=False, pantry=()):
    selected = {normalise(x) for x in selected}
    available = selected | {normalise(x) for x in pantry}
    result = []
    for recipe in recipes:
        ingredients = {normalise(x['name']) for x in recipe['ingredients']}
        if query.casefold().strip() not in recipe['name'].casefold():
            continue
        if only and not ingredients <= available:
            continue
        if not only and not selected <= ingredients:
            continue
        result.append((recipe, sorted(ingredients - available)))
    return sorted(result, key=lambda item: item[0]['name'].casefold())

class Store:
    def __init__(self, settings):
        self.settings = settings
        self.cloud = bool(settings.get('supabase_url') and settings.get('supabase_service_key'))
        if not self.cloud:
            self.path = Path(__file__).parent / 'preview.sqlite3'
            with sqlite3.connect(self.path) as db:
                db.execute('create table if not exists recipes (id text primary key, data text not null)')

    def request(self, method='GET', payload=None, recipe_id=None):
        url = self.settings['supabase_url'].rstrip('/') + '/rest/v1/recipe_book_meals'
        url += '?' + urlencode({'id': 'eq.' + recipe_id} if recipe_id else {'select': '*'})
        key = self.settings['supabase_service_key']
        headers = {'apikey': key, 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        request = Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
        with urlopen(request, timeout=20) as response:
            body = response.read()
            return json.loads(body) if body else []

    def all(self):
        if self.cloud:
            return self.request()
        with sqlite3.connect(self.path) as db:
            return [json.loads(row[0]) for row in db.execute('select data from recipes')]

    def save(self, recipe, existing=False):
        if self.cloud:
            self.request('PATCH' if existing else 'POST', recipe, recipe['id'] if existing else None)
        else:
            with sqlite3.connect(self.path) as db:
                db.execute('insert or replace into recipes values (?, ?)', (recipe['id'], json.dumps(recipe)))

    def delete(self, recipe_id):
        if self.cloud:
            self.request('DELETE', recipe_id=recipe_id)
        else:
            with sqlite3.connect(self.path) as db:
                db.execute('delete from recipes where id = ?', (recipe_id,))
