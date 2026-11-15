# Local copy of saucedemo.com so the suite can run without internet.
#
# It keeps what the tests rely on: same URLs, same ids / data-test attributes / CSS classes,
# same error messages, same validation order and the same 8% tax.
#
# Run it alone:  python app/server.py   ->  http://127.0.0.1:5055/
# The test suite starts it by itself when nothing is listening on that port.

import json
import os
import re
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'Data')
DEFAULT_PORT = 5055

app = Flask(__name__)
app.secret_key = 'local-copy-not-a-secret'  # only signs the session cookie of this local app

TAX_RATE = 0.08
LOCKED_USERS = {'locked_out_user'}

ERR_LOCKED = 'Epic sadface: Sorry, this user has been locked out.'
ERR_NO_MATCH = 'Epic sadface: Username and password do not match any user in this service'
ERR_USER_REQUIRED = 'Epic sadface: Username is required'
ERR_PASSWORD_REQUIRED = 'Epic sadface: Password is required'


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding='utf-8') as f:
        return json.load(f)


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


# Products and users come from Data/*.json, the same files the tests read
PRODUCTS = [{'slug': slugify(p['name']), 'name': p['name'], 'price': p['price'],
             'description': f"carry.allTheThings() with the {p['name']}."}
            for p in load_json('products.json')]
BY_SLUG = {p['slug']: p for p in PRODUCTS}
USERS = {name: info['password'] for name, info in load_json('users.json').items()}

SORTS = {
    'az': lambda items: sorted(items, key=lambda p: p['name']),
    'za': lambda items: sorted(items, key=lambda p: p['name'], reverse=True),
    'lohi': lambda items: sorted(items, key=lambda p: (p['price'], p['name'])),
    'hilo': lambda items: sorted(items, key=lambda p: (-p['price'], p['name'])),
}


def money(value):
    return f'{value:.2f}'


app.jinja_env.globals['money'] = money


def cart():
    return session.setdefault('cart', [])


def cart_items():
    return [BY_SLUG[s] for s in cart() if s in BY_SLUG]


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_cart():
    return {'cart_count': len(cart())}


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None, username='')

    username = request.form.get('user-name', '')
    password = request.form.get('password', '')
    error = None
    if username == '':
        error = ERR_USER_REQUIRED
    elif password == '':
        error = ERR_PASSWORD_REQUIRED
    elif username in LOCKED_USERS and USERS.get(username) == password:
        error = ERR_LOCKED
    elif USERS.get(username) != password:
        error = ERR_NO_MATCH
    if error:
        return render_template('login.html', error=error, username=username)

    session.clear()
    session['user'] = username
    session['cart'] = []
    return redirect(url_for('inventory'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/inventory.html')
@login_required
def inventory():
    order = SORTS.get(request.args.get('sort', 'az'), SORTS['az'])
    return render_template('inventory.html', products=order(PRODUCTS), in_cart=set(cart()))


@app.route('/cart/toggle/<slug>', methods=['POST'])
@login_required
def toggle_cart(slug):
    if slug in BY_SLUG:
        if slug in cart():
            cart().remove(slug)
        else:
            cart().append(slug)
        session.modified = True
    return redirect(request.form.get('back') or url_for('inventory'))


@app.route('/cart.html')
@login_required
def cart_page():
    return render_template('cart.html', items=cart_items())


@app.route('/checkout-step-one.html', methods=['GET', 'POST'])
@login_required
def checkout_step_one():
    first = last = postal = ''
    error = None
    if request.method == 'POST':
        first = request.form.get('firstName', '')
        last = request.form.get('lastName', '')
        postal = request.form.get('postalCode', '')
        # Fields are checked in order and only the first error is shown, like the real site
        if first == '':
            error = 'Error: First Name is required'
        elif last == '':
            error = 'Error: Last Name is required'
        elif postal == '':
            error = 'Error: Postal Code is required'
        else:
            session['customer'] = {'firstName': first, 'lastName': last, 'postalCode': postal}
            return redirect(url_for('checkout_step_two'))
    return render_template('checkout_step_one.html', error=error, first=first, last=last, postal=postal)


@app.route('/checkout-step-two.html')
@login_required
def checkout_step_two():
    items = cart_items()
    subtotal = round(sum(p['price'] for p in items), 2)
    tax = round(subtotal * TAX_RATE, 2)
    return render_template('checkout_step_two.html', items=items,
                           subtotal=subtotal, tax=tax, total=round(subtotal + tax, 2))


@app.route('/checkout-complete.html', methods=['GET', 'POST'])
@login_required
def checkout_complete():
    if request.method == 'POST':  # Finish: the order is placed and the cart is emptied
        session['cart'] = []
        return redirect(url_for('checkout_complete'))
    return render_template('checkout_complete.html')


def main():
    app.run(host='127.0.0.1', port=int(os.environ.get('APP_PORT', DEFAULT_PORT)))


if __name__ == '__main__':
    main()
