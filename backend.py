from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from string import ascii_uppercase
from random import choice
from werkzeug.security import generate_password_hash, check_password_hash
import json
from dataclasses import dataclass

@dataclass
class WebSite:
    title : str
    titlebar_color : str
    title_text_color : str
    footer_text : str

class UserNotFound(Exception):
    def __init__(self, name):
        super().__init__(f"User {name} Not Found")

class MoneyError(Exception):
    def __init__(self, user, required):
        super().__init__(f"{user.name} does not have ${required} money.\nCurrent Balance = {user.wallet.money}\nMissing = {required - user.wallet.money}")

class OrderError(Exception):
    def __init__(self, id):
        super().__init__(f"Order {id} not found!")

class idfk(Flask):
    def __init__(self):
        super().__init__(__name__)
        self.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
        self.db = SQLAlchemy(self)
        self.config["SECRET_KEY"] = "IDK123"
        temp = (lambda x : json.loads(x.read()))(open('website.json','r'))
        self.website_data = WebSite(*(temp.values()))
        self.items = (lambda x : json.loads(x.read()))(open('data.json','r'))

    def add_user(self, name : str, password : str, location : str):
        name = name.lower()
        new_user = User(name = name, password = generate_password_hash(password),location=location)
        new_wallet = Wallet(name = name, _money=0)
        new_cart = Cart(name = name)
        self.db.session.add_all([new_user,new_wallet,new_cart])
        self.db.session.commit()

    def add_money_to_user(self, name, amount):
        name = name.lower()
        if not (existing := self.db.session.query(User).filter_by(name = name).first()):
            raise UserNotFound(name)
        existing.wallet.money += amount
        return True

    def add_item(self, name : str, price : int, thumbnail : str = ""):
        new_item = Item(name= name, price=price, thumbnail= thumbnail)
        print(new_item)
        with self.app_context():
            self.db.session.add(new_item)
            self.db.session.commit()

    def buy(self, name, items):
        name = name.lower()
        if not (existing := self.db.session.query(User).filter_by(name = name).first()):
            raise UserNotFound(name)
        data = []
        total = 0
        new_order = Order(name = name)
        self.db.session.add(new_order)
        for item in items:
            existing_item = self.db.session.query(Item).filter_by(name = item).first()
            new_order.items.append(existing_item)
            data.append(existing_item)
            total += existing_item.price

        if existing.wallet.money < total:
            raise MoneyError(existing , total)

        existing.wallet.money -= total
        self.db.session.add(new_order)
        self.db.session.commit()

    def complete_order(self, id):
        if not (order := self.db.session.query(Order).filter_by(_id = id).first()):
            raise OrderError(id)
        self.db.session.delete(order)
        self.db.session.commit()

app = idfk()

class User(app.db.Model):
    __tablename__ = "user"
    name = app.db.Column(app.db.String(16), primary_key = True)
    password = app.db.Column(app.db.String(162))
    location = app.db.Column(app.db.String(50))
    wallet = app.db.relationship("Wallet", back_populates = "user", uselist = False)
    cart = app.db.relationship("Cart", back_populates = "user" , uselist=False)
    order = app.db.relationship("Order", back_populates = "user")


class Wallet(app.db.Model):
    __tablename__ = "wallet"
    user = app.db.relationship("User", uselist = False)
    name = app.db.Column(app.db.ForeignKey("user.name"), primary_key = True)
    _money = app.db.Column(app.db.Integer)

    @property
    def money(self):
        return self._money

    @money.setter
    def money(self,value):
        self._money = max(0, value)
        app.db.session.commit()

    def __repr__(self):
        return f"{self.name} - ${self.money}"

class CartRelation(app.db.Model):
    __tablename__ = "cartrelation"
    _id =  app.db.Column("id", app.db.Integer, primary_key=True)
    cart_name = app.db.Column("cart_name", app.db.ForeignKey("cart.name"))
    item_name =  app.db.Column("item_name", app.db.ForeignKey("item.name"))
    quantity = app.db.Column("quantity", app.db.Integer, default=1)

class OrderRelation(app.db.Model):
    __tablename__ = "orderrelation"
    _id = app.db.Column(app.db.Integer, primary_key= True)
    username = app.db.Column(app.db.ForeignKey("order.name"))
    item_name = app.db.Column(app.db.ForeignKey("item.name"))
    quantity = app.db.Column(app.db.Integer, default=1)


class Item(app.db.Model):
    __tablename__ = "item"
    name = app.db.Column(app.db.String(30), primary_key = True)
    price = app.db.Column(app.db.Integer)
    thumbnail = app.db.Column(app.db.String(100))
    carts = app.db.relationship("Cart", secondary = "cartrelation", back_populates = "items")
    orders = app.db.relationship("Order", secondary = "orderrelation", back_populates = "items")

    def __repr__(self):
        return f"{self.name} - ${self.price}"

    def __str__(self):
        return f"{self.name} - ${self.price}"

class Cart(app.db.Model):
    __tablename__ = "cart"
    user = app.db.relationship("User", back_populates = "cart", uselist = False)
    name = app.db.Column(app.db.ForeignKey("user.name"), primary_key = True)
    items = app.db.relationship("Item", secondary = "cartrelation", back_populates = "carts")

    def __repr__(self):
        return f"Cart for {self.name}:\n{'\n'.join([str(item) for item in self.items])}"

class Order(app.db.Model):
    __tablename__ = "order"
    _id = app.db.Column(app.db.Integer, primary_key = True)
    user = app.db.relationship("User", uselist = False, back_populates = "order")
    name = app.db.Column(app.db.ForeignKey("user.name"))
    items = app.db.relationship("Item", secondary = "orderrelation", back_populates = "orders")

    def __repr__(self):
        return f"Order {self._id}:\n{'\n'.join([str(item) for item in self.items])}"

@app.before_request
def verify_session():
    exclude = ['login','signup']
    name = session.get("name")
    if request.endpoint not in exclude:
        existing = app.db.session.query(User).filter_by(name = name).first() if name else None
        if not existing:
            return redirect(url_for('login'))

app.route('/')(lambda : redirect(url_for('login' if not session.get('name') else 'index')))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not (name := request.form.get("name")) or len(name)>=17:
            flash("Enter a valid name under 16 characters")
            return redirect(url_for('login'))
        if not (password := request.form.get("password")) or len(password)<4:
            flash("Enter a valid password of length greater than or equal to 4")
            return redirect(url_for('login'))
        user = app.db.session.query(User).filter_by(name=name).first()
        if not user or not check_password_hash(user.password, password):
            flash("invalid username or password")
            return redirect(url_for('login'))
        session["name"] = name
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if not (name := request.form.get("name")) or len(name)>=17:
            flash("Enter a valid name under 16 characters")
            return redirect(url_for('signup'))
        if not (password := request.form.get("password")) or len(password)<4:
            flash("Enter a valid password of length greater than or equal to 4")
            return redirect(url_for('signup'))
        user = app.db.session.query(User).filter_by(name=name).first()
        if user:
            flash("user already taken")
            return redirect(url_for('signup'))
        app.add_user(name,password,"")
        session["name"] = name
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/shop')
def index():
    print(app.items)
    return render_template('shop.html',items = app.items, data=app.website_data )

@app.route('/add_to_cart',methods=["POST"])
def add_to_cart():
    print(request.form)
    if not (item_name := request.form.get("item")) or not (name := session.get("name")):
        return jsonify({"status" : "failure"}),400
    user = app.db.session.query(User).filter_by(name = name).first()
    item = app.db.session.query(Item).filter_by(name = item_name).first()
    existing_cart = app.db.session.query(CartRelation).filter_by(cart_name = name, item_name = item_name).first()
    if not existing_cart:
        user.cart.items.append(item)
    else:
        existing_cart.quantity += 1
    app.db.session.commit()
    return jsonify({"status" : "success"}), 200

def startup():
    with open('data.json','r') as file:
        items = json.loads(file.read())
    for item in items:
        app.add_item(*(item["name"], item["price"], item["thumbnail"]))


if __name__ == '__main__':
    with app.app_context():
        app.db.create_all()
        startup()
    app.run(port = 8080)
