# Imports
import os
import base64
from datetime import datetime
from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash, make_response
from sqlalchemy import create_engine, asc, desc, DateTime
from sqlalchemy.orm import sessionmaker, scoped_session
from database_setup import Base, Category, Items, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps

app = Flask(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
client_secrets = os.path.join(current_dir, 'client_secrets.json')

CLIENT_ID = json.loads(
    open(client_secrets, 'r').read())['web']['client_id']
APPLICATION_NAME = "udacity-catalog-app"


# Connect to the database.
# Create database session.
engine = create_engine('sqlite:///catalog.db',
                       connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = scoped_session(sessionmaker(bind=engine))
session = DBSession()


def login_required(f):
    '''Checks to see whether a user is logged in'''
    @wraps(f)
    def x(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return x


# Create anti-forgery state token
@app.route('/login')
def showLogin():

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# gconnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(client_secrets, scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                  'Current user is already connected. '), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '''"style = "width: 300px;
                            height: 300px;border-radius: 150px;
                            -webkit-border-radius: 150px;
                            -moz-border-radius: 150px;">'''
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


# Main Page Showing All Categories
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Items).order_by(desc(Items.date)).limit(5)

    if 'username' not in login_session:
        return render_template('public_catalog.html',
                               categories=categories,
                               items=items)
    else:
        return render_template('catalog.html',
                               categories=categories,
                               items=items)


# Create a category
@app.route('/catalog/new/', methods=['GET', 'POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Item Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('newcategory.html')


# Edit a category
@app.route('/catalog/<int:category_id>/edit/', methods=['GET', 'POST'])
@login_required
def editCategory(category_id):
    editedCategory = session.query(
        Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return '''<script>function myFunction()
                {alert('You are not authorized to edit this item catogry.
                Please create your own item category in order to edit.');}
                </script><body onload='myFunction()'>'''
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Item Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showCatalog'))
    else:
        return render_template('editcategory.html', category=editedCategory)


# Delete a category
@app.route('/catalog/<int:category_id>/delete/', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_id):
    categoryToDelete = session.query(
        Category).filter_by(id=category_id).one()
    itemsToDelete = session.query(Items).filter_by(
        category_id=category_id).delete()
    if categoryToDelete.user_id != login_session['user_id']:
        return '''<script>function myFunction()
                {alert('You are not authorized to delete this item category.
                Please create your own item category in order to delete.');}
                </script><body onload='myFunction()'>'''
    if request.method == 'POST':
        session.delete(categoryToDelete)
        session.commit()
        flash('%s Successfully Deleted' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCatalog', category_id=category_id))
    else:
        return render_template('deletecategory.html',
                               category=categoryToDelete)


# Shows items for a category
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def showItems(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Items).filter_by(
        category_id=category_id).all()
    if ('username' 
        not in login_session 
        or creator.id != login_session['user_id']):
        return render_template('publicitems.html',
                               items=items,
                               category=category,
                               creator=creator)
    else:
        return render_template('items.html',
                               items=items,
                               category=category,
                               creator=creator)


# Create new items for a category
@app.route('/catalog/<int:category_id>/menu/new/', methods=['GET', 'POST'])
@login_required
def newItem(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return '''<script>function myFunction()
            {alert('You are not authorized to add items to this category.
            Please create your own items category in order to add items.');}
            </script><body onload='myFunction()'>'''
    if request.method == 'POST':
        newItem = Items(name=request.form['name'],
                        description=request.form['description'],
                        picture_url=request.form['picture_url'],
                        date=datetime.now(),
                        category_id=category_id,
                        user_id=category.user_id)
        session.add(newItem)
        session.commit()
        flash('New %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showCatalog', category_id=category_id))
    else:
        return render_template('newitem.html', category_id=category_id)


# Edit items of a category
@app.route('/catalog/<int:category_id>/menu/<int:items_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_id, items_id):
    editedItem = session.query(Items).filter_by(id=items_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return '''<script>function myFunction()
                {alert('You are not authorized to edit items to this category.
                Please create your own items category
                in order to edit items.');}
                </script><body onload='myFunction()'>'''
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['picture_url']:
            editedItem.picture_url = request.form['picture_url']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showCatalog', category_id=category_id))
    else:
        return render_template('edititem.html',
                               category_id=category_id,
                               items_id=items_id,
                               item=editedItem)


# Delete items of a category
@app.route('/catalog/<int:category_id>/menu/<int:items_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_id, items_id):
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Items).filter_by(id=items_id).one()
    if login_session['user_id'] != category.user_id:
        return '''<script>function myFunction()
            {alert('You are not authorized to delete items to this category.
            Please create your own category in order to delete items.');}
            </script><body onload='myFunction()'>'''
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showCatalog', category_id=category_id))
    else:
        return render_template('deleteitem.html', item=itemToDelete)


# JSON APIs to view Catalog Information
@app.route('/catalog/JSON')
def catalogJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
app.run(host='0.0.0.0', port=5000)
