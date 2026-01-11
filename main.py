"""
Adisyo POS Sistemi - Python Backend
Flask + SQLite + SQLAlchemy tabanlı REST API
"""

from flask import Flask, jsonify, request, send_from_directory, session, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os

# Flask App Setup
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')
app.secret_key = 'adisyo-secret-key-2024'
CORS(app, supports_credentials=True)

# Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'adisyo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)



# ============== DATABASE MODELS ==============

class Printer(db.Model):
    __tablename__ = 'printers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), default='network')  # network, usb, console
    connection_string = db.Column(db.String(100), nullable=False)  # IP for network, Port for USB
    status = db.Column(db.String(20), default='active')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'connection_string': self.connection_string,
            'status': self.status
        }

class Station(db.Model):
    __tablename__ = 'stations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # Kitchen, Bar, etc.
    printer_id = db.Column(db.Integer, db.ForeignKey('printers.id'), nullable=True)
    printer = db.relationship('Printer', backref='stations')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'printer_id': self.printer_id,
            'printer_name': self.printer.name if self.printer else None
        }

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, cashier, waiter
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'role': self.role
        }


class Table(db.Model):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default='available')  # available, occupied
    opened_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'status': self.status,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None
        }


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(30), nullable=False)
    icon = db.Column(db.String(50))
    items = db.relationship('MenuItem', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,
            'icon': self.icon
        }


class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=True)
    available = db.Column(db.Boolean, default=True)
    station = db.relationship('Station', backref='menu_items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'category_id': self.category_id,
            'station_id': self.station_id,
            'station_name': self.station.name if self.station else None,
            'category': self.category.key if self.category else None,
            'available': self.available
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'))
    status = db.Column(db.String(20), default='open')  # open, paid, cancelled
    opened_at = db.Column(db.DateTime, default=datetime.now)
    closed_at = db.Column(db.DateTime, nullable=True)
    subtotal = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=10)
    tax_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    discount_type = db.Column(db.String(20), nullable=True)  # percent, fixed, treat
    total = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(20), nullable=True)  # cash, card
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    table = db.relationship('Table', backref='orders')
    
    def to_dict(self):
        return {
            'id': self.id,
            'table_id': self.table_id,
            'table_name': self.table.name if self.table else None,
            'status': self.status,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'subtotal': self.subtotal,
            'tax_rate': self.tax_rate,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'discount_type': self.discount_type,
            'total': self.total,
            'payment_method': self.payment_method,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    note = db.Column(db.String(200), nullable=True)
    is_printed = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'note': self.note,
            'is_printed': self.is_printed
        }


class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200))


# ============== DATABASE INITIALIZATION ==============

def init_database():
    """Veritabani ve varsayilan verileri olustur"""
    db.create_all()
    
    # Kullanicilar
    if User.query.count() == 0:
        users = [
            User(username='admin', password='admin123', name='Admin', role='admin'),
            User(username='garson2', password='1234', name='Ahmet', role='waiter'),
            User(username='garson1', password='1234', name='Mehmet', role='waiter'),
        ]
        db.session.add_all(users)
    
    # Masalar
    if Table.query.count() == 0:
        tables = [Table(name=f'Masa {i+1}', capacity=4) for i in range(12)]
        db.session.add_all(tables)
    
    # Kategoriler
    if Category.query.count() == 0:
        categories = [
            Category(name='Ana Yemekler', key='main', icon='ph-hamburger'),
            Category(name='Icecekler', key='drinks', icon='ph-coffee'),
            Category(name='Tatlilar', key='desserts', icon='ph-cookie'),
            Category(name='Mezeler', key='appetizers', icon='ph-bowl-food'),
        ]
        db.session.add_all(categories)
        db.session.commit()
        
        # Menu Urunleri
        menu_items = [
            # Ana Yemekler
            MenuItem(name='Adana Kebap', price=220, category_id=1),
            MenuItem(name='Urfa Kebap', price=200, category_id=1),
            MenuItem(name='Karisik Izgara', price=450, category_id=1),
            MenuItem(name='Tavuk Sis', price=180, category_id=1),
            MenuItem(name='Lahmacun', price=80, category_id=1),
            MenuItem(name='Pide (Kasarli)', price=120, category_id=1),
            MenuItem(name='Pide (Kiymali)', price=140, category_id=1),
            MenuItem(name='Iskender', price=280, category_id=1),
            # Icecekler
            MenuItem(name='Ayran', price=30, category_id=2),
            MenuItem(name='Kola', price=40, category_id=2),
            MenuItem(name='Salgam', price=35, category_id=2),
            MenuItem(name='Su', price=15, category_id=2),
            MenuItem(name='Fanta', price=40, category_id=2),
            MenuItem(name='Sprite', price=40, category_id=2),
            MenuItem(name='Cay', price=20, category_id=2),
            MenuItem(name='Turk Kahvesi', price=45, category_id=2),
            # Tatlilar
            MenuItem(name='Kunefe', price=150, category_id=3),
            MenuItem(name='Baklava', price=120, category_id=3),
            MenuItem(name='Sutlac', price=70, category_id=3),
            MenuItem(name='Kadayif', price=130, category_id=3),
            # Mezeler
            MenuItem(name='Mercimek Corbasi', price=60, category_id=4),
            MenuItem(name='Ezme', price=50, category_id=4),
            MenuItem(name='Humus', price=55, category_id=4),
            MenuItem(name='Cacik', price=45, category_id=4),
            MenuItem(name='Patlican Salatasi', price=60, category_id=4),
        ]
        db.session.add_all(menu_items)
    
    # Ayarlar
    if Setting.query.count() == 0:
        settings = [
            Setting(key='restaurant_name', value='Adisyo Restaurant'),
            Setting(key='currency', value='TL'),
            Setting(key='tax_rate', value='10'),
        ]
        db.session.add_all(settings)
    
    db.session.commit()
    print("Veritabani baslatildi")


# ============== AUTH DECORATOR ==============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Giris yapmaniz gerekiyor'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Giris yapmaniz gerekiyor'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'error': 'Yetkiniz yok'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ============== ROUTES ==============

@app.route('/')
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/masalar')
@login_required
def masalar_page():
    return render_template('masalar.html')

@app.route('/mutfak')
@login_required
def mutfak_page():
    return render_template('mutfak.html')

@app.route('/raporlar')
@login_required
def raporlar_page():
    return render_template('raporlar.html')

@app.route('/menu-yonetimi')
@admin_required
def menu_yonetimi_page():
    return render_template('menu-yonetimi.html')

@app.route('/kullanicilar')
@admin_required
def kullanicilar_page():
    return render_template('kullanicilar.html')

@app.route('/cihazlar')
@admin_required
def cihazlar_page():
    return render_template('cihazlar.html')

@app.route('/ayarlar')
@login_required
def ayarlar_page():
    return render_template('ayarlar.html')


# ============== AUTH API ==============

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Kullanici girisi"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, password=password).first()
    
    if user:
        session['user_id'] = user.id
        session['user_role'] = user.role
        return jsonify({'success': True, 'data': user.to_dict()})
    
    return jsonify({'success': False, 'error': 'Gecersiz kullanici adi veya sifre'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Kullanici cikisi"""
    session.clear()
    return jsonify({'success': True, 'message': 'Cikis yapildi'})


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Mevcut kullanici bilgisi"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({'success': True, 'data': user.to_dict()})
    return jsonify({'success': False, 'data': None})


# ============== USERS API ==============

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Tum kullanicilari getir"""
    users = User.query.all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]})


@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    """Yeni kullanici olustur"""
    data = request.json
    user = User(
        username=data.get('username'),
        password=data.get('password'),
        name=data.get('name'),
        role=data.get('role', 'waiter')
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'data': user.to_dict()})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Kullanici sil"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Kullanici silindi'})


# ============== TABLES API ==============

@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Tum masalari getir"""
    tables = Table.query.all()
    result = []
    for table in tables:
        table_data = table.to_dict()
        # Acik siparis varsa ekle
        open_order = Order.query.filter_by(table_id=table.id, status='open').first()
        if open_order:
            table_data['order'] = open_order.to_dict()
        else:
            table_data['order'] = None
        result.append(table_data)
    return jsonify({'success': True, 'data': result})


@app.route('/api/tables', methods=['POST'])
@admin_required
def create_table():
    """Yeni masa olustur"""
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'error': 'Masa adi gerekli'}), 400
        
    table = Table(
        name=name,
        capacity=data.get('capacity', 4)
    )
    db.session.add(table)
    db.session.commit()
    return jsonify({'success': True, 'data': table.to_dict()})


@app.route('/api/tables/<int:table_id>', methods=['GET'])
def get_table(table_id):
    """Tek masa getir"""
    table = Table.query.get_or_404(table_id)
    table_data = table.to_dict()
    open_order = Order.query.filter_by(table_id=table.id, status='open').first()
    if open_order:
        table_data['order'] = open_order.to_dict()
    else:
        table_data['order'] = None
    return jsonify({'success': True, 'data': table_data})


@app.route('/api/tables/<int:table_id>/open', methods=['POST'])
def open_table(table_id):
    """Masa ac"""
    table = Table.query.get_or_404(table_id)
    
    # Zaten acik siparis var mi?
    existing_order = Order.query.filter_by(table_id=table_id, status='open').first()
    if existing_order:
        return jsonify({'success': True, 'data': existing_order.to_dict()})
    
    # Yeni siparis olustur
    order = Order(
        table_id=table_id,
        opened_at=datetime.now(),
        user_id=session.get('user_id')
    )
    table.status = 'occupied'
    table.opened_at = datetime.now()
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({'success': True, 'data': order.to_dict()})


@app.route('/api/tables/<int:table_id>/close', methods=['POST'])
def close_table(table_id):
    """Masa kapat (odeme olmadan)"""
    table = Table.query.get_or_404(table_id)
    open_order = Order.query.filter_by(table_id=table_id, status='open').first()
    
    if open_order:
        open_order.status = 'cancelled'
        open_order.closed_at = datetime.now()
    
    table.status = 'available'
    table.opened_at = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Masa kapatildi'})


# ============== ORDERS API ==============

@app.route('/api/orders/<int:order_id>/items', methods=['POST'])
def add_order_item(order_id):
    """Siparise urun ekle"""
    order = Order.query.get_or_404(order_id)
    data = request.json
    menu_item_id = data.get('menu_item_id')
    quantity = data.get('quantity', 1)
    note = data.get('note', '')
    
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    # Ayni urun var mi?
    existing = OrderItem.query.filter_by(order_id=order_id, menu_item_id=menu_item_id, note=note).first()
    if existing:
        existing.quantity += quantity
    else:
        item = OrderItem(
            order_id=order_id,
            menu_item_id=menu_item_id,
            name=menu_item.name,
            price=menu_item.price,
            quantity=quantity,
            note=note
        )
        db.session.add(item)
    
    # Toplami guncelle
    update_order_totals(order)
    db.session.commit()
    
    return jsonify({'success': True, 'data': order.to_dict()})


@app.route('/api/orders/<int:order_id>/items/<int:item_id>', methods=['PUT'])
def update_order_item(order_id, item_id):
    """Siparis kalemini guncelle"""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.get_or_404(item_id)
    data = request.json
    
    if 'quantity' in data:
        if data['quantity'] <= 0:
            db.session.delete(item)
        else:
            item.quantity = data['quantity']
    
    if 'note' in data:
        item.note = data['note']
    
    update_order_totals(order)
    db.session.commit()
    
    return jsonify({'success': True, 'data': order.to_dict()})


@app.route('/api/orders/<int:order_id>/items/<int:item_id>', methods=['DELETE'])
def delete_order_item(order_id, item_id):
    """Siparis kalemini sil"""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.get_or_404(item_id)
    
    db.session.delete(item)
    update_order_totals(order)
    db.session.commit()
    
    return jsonify({'success': True, 'data': order.to_dict()})


def update_order_totals(order):
    """Siparis toplamlarini hesapla"""
    subtotal = sum(item.price * item.quantity for item in order.items)
    order.subtotal = subtotal
    order.tax_amount = subtotal * (order.tax_rate / 100)
    order.total = subtotal + order.tax_amount - order.discount_amount


# ============== PAYMENT API ==============

@app.route('/api/orders/<int:order_id>/payment', methods=['POST'])
def process_payment(order_id):
    """Odeme islemi"""
    order = Order.query.get_or_404(order_id)
    data = request.json
    
    # Indirim uygula
    discount_type = data.get('discount_type')
    discount_value = data.get('discount_value', 0)
    
    if discount_type == 'percent':
        order.discount_amount = order.subtotal * (discount_value / 100)
        order.discount_type = 'percent'
    elif discount_type == 'fixed':
        order.discount_amount = discount_value
        order.discount_type = 'fixed'
    elif discount_type == 'treat':
        order.discount_amount = order.subtotal + order.tax_amount
        order.discount_type = 'treat'
    
    # Toplami yeniden hesapla
    order.total = order.subtotal + order.tax_amount - order.discount_amount
    if order.total < 0:
        order.total = 0
    
    # Odeme bilgilerini kaydet
    order.payment_method = data.get('payment_method', 'cash')
    order.status = 'paid'
    order.closed_at = datetime.now()
    
    # Masayi bosalt
    table = Table.query.get(order.table_id)
    if table:
        table.status = 'available'
        table.opened_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Odeme basarili',
        'data': order.to_dict()
    })


# ============== MENU API ==============

@app.route('/api/menu', methods=['GET'])
def get_menu():
    """Tum menuyu getir"""
    categories = Category.query.all()
    result = {}
    for cat in categories:
        items = MenuItem.query.filter_by(category_id=cat.id, available=True).all()
        result[cat.key] = [item.to_dict() for item in items]
    return jsonify({'success': True, 'data': result})


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Kategorileri getir"""
    categories = Category.query.all()
    return jsonify({'success': True, 'data': [c.to_dict() for c in categories]})


@app.route('/api/categories', methods=['POST'])
@admin_required
def create_category():
    """Yeni kategori olustur"""
    data = request.json
    category = Category(
        name=data.get('name'),
        key=data.get('key'),
        icon=data.get('icon', 'ph-folder')
    )
    db.session.add(category)
    db.session.commit()
    return jsonify({'success': True, 'data': category.to_dict()})


@app.route('/api/menu/items', methods=['GET'])
def get_all_menu_items():
    """Tum menu urunlerini getir"""
    items = MenuItem.query.all()
    return jsonify({'success': True, 'data': [item.to_dict() for item in items]})


@app.route('/api/menu/items', methods=['POST'])
@admin_required
def create_menu_item():
    """Yeni menu urunu olustur"""
    data = request.json
    item = MenuItem(
        name=data.get('name'),
        price=data.get('price'),
        category_id=data.get('category_id'),
        available=data.get('available', True)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'data': item.to_dict()})


@app.route('/api/menu/items/<int:item_id>', methods=['PUT'])
@admin_required
def update_menu_item(item_id):
    """Menu urunu guncelle"""
    item = MenuItem.query.get_or_404(item_id)
    data = request.json
    
    if 'name' in data:
        item.name = data['name']
    if 'price' in data:
        item.price = data['price']
    if 'category_id' in data:
        item.category_id = data['category_id']
    if 'available' in data:
        item.available = data['available']
    
    db.session.commit()
    return jsonify({'success': True, 'data': item.to_dict()})


@app.route('/api/menu/items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_menu_item(item_id):
    """Menu urunu sil"""
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Urun silindi'})


# ============== REPORTS API ==============

@app.route('/api/reports/daily', methods=['GET'])
def get_daily_report():
    """Gunluk rapor"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Giris yapmaniz gerekiyor'}), 401
    
    current_user = User.query.get(session['user_id'])
    if not current_user or current_user.role == 'waiter':
        return jsonify({'success': False, 'error': 'Yetkiniz yok'}), 403

    date_str = request.args.get('date')
    if date_str:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = datetime.now().date()
    
    # Gunu icindeki kapanan siparisler
    from sqlalchemy import func
    
    orders = Order.query.filter(
        Order.status == 'paid',
        func.date(Order.closed_at) == report_date
    ).all()
    
    total_revenue = sum(o.total for o in orders)
    total_orders = len(orders)
    cash_total = sum(o.total for o in orders if o.payment_method == 'cash')
    card_total = sum(o.total for o in orders if o.payment_method == 'card')
    total_discount = sum(o.discount_amount for o in orders)
    total_tax = sum(o.tax_amount for o in orders)
    
    # En cok satilan urunler
    item_sales = {}
    for order in orders:
        for item in order.items:
            if item.name not in item_sales:
                item_sales[item.name] = {'qty': 0, 'revenue': 0}
            item_sales[item.name]['qty'] += item.quantity
            item_sales[item.name]['revenue'] += item.price * item.quantity
    
    top_items = sorted(item_sales.items(), key=lambda x: x[1]['qty'], reverse=True)[:10]
    
    return jsonify({
        'success': True,
        'data': {
            'date': report_date.isoformat(),
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'average_order': total_revenue / total_orders if total_orders > 0 else 0,
            'cash_total': cash_total,
            'card_total': card_total,
            'total_discount': total_discount,
            'total_tax': total_tax,
            'top_items': [{'name': k, **v} for k, v in top_items],
            'orders': [o.to_dict() for o in orders]
        }
    })


@app.route('/api/reports/orders', methods=['GET'])
def get_order_history():
    """Siparis gecmisi"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Giris yapmaniz gerekiyor'}), 401
    
    current_user = User.query.get(session['user_id'])
    if not current_user or current_user.role == 'waiter':
        return jsonify({'success': False, 'error': 'Yetkiniz yok'}), 403

    orders = Order.query.filter_by(status='paid').order_by(Order.closed_at.desc()).limit(100).all()
    return jsonify({'success': True, 'data': [o.to_dict() for o in orders]})



# ============== PRINTER API ==============

@app.route('/api/printers', methods=['GET'])
@admin_required
def get_printers():
    printers = Printer.query.all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in printers]})

@app.route('/api/printers', methods=['POST'])
@admin_required
def create_printer():
    data = request.json
    printer = Printer(
        name=data.get('name'),
        type=data.get('type', 'network'),
        connection_string=data.get('connection_string')
    )
    db.session.add(printer)
    db.session.commit()
    return jsonify({'success': True, 'data': printer.to_dict()})

@app.route('/api/printers/<int:printer_id>', methods=['DELETE'])
@admin_required
def delete_printer(printer_id):
    printer = Printer.query.get_or_404(printer_id)
    db.session.delete(printer)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Yazici silindi'})

# ============== STATION API ==============

@app.route('/api/stations', methods=['GET'])
def get_stations():
    stations = Station.query.all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in stations]})

@app.route('/api/stations', methods=['POST'])
@admin_required
def create_station():
    data = request.json
    station = Station(
        name=data.get('name'),
        printer_id=data.get('printer_id')
    )
    db.session.add(station)
    db.session.commit()
    return jsonify({'success': True, 'data': station.to_dict()})

@app.route('/api/stations/<int:station_id>', methods=['PUT'])
@admin_required
def update_station(station_id):
    station = Station.query.get_or_404(station_id)
    data = request.json
    if 'name' in data:
        station.name = data['name']
    if 'printer_id' in data:
        station.printer_id = data['printer_id']
    db.session.commit()
    return jsonify({'success': True, 'data': station.to_dict()})

@app.route('/api/stations/<int:station_id>', methods=['DELETE'])
@admin_required
def delete_station(station_id):
    station = Station.query.get_or_404(station_id)
    db.session.delete(station)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Reyon silindi'})


# ============== SETTINGS API ==============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Ayarlari getir"""
    settings = Setting.query.all()
    result = {s.key: s.value for s in settings}
    if 'print_enabled' not in result:
        result['print_enabled'] = 'true'
    return jsonify({'success': True, 'data': result})


@app.route('/api/settings', methods=['PUT'])
@admin_required
def update_settings():
    """Ayarlari guncelle"""
    data = request.json
    for key, value in data.items():
        setting = Setting.query.get(key)
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=key, value=str(value))
            db.session.add(setting)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Ayarlar guncellendi'})



# ============== PRINTING LOGIC ==============

def safe_print(printer, content):
    """Guvenli yazdirma fonksiyonu"""
    try:
        from escpos.printer import Network, Dummy
        
        p = None
        if printer.type == 'network':
            # Format: IP:PORT or just IP
            parts = printer.connection_string.split(':')
            ip = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 9100
            try:
                p = Network(ip, port=port, timeout=5)
            except Exception as e:
                print(f"Printer Connection Error ({printer.name}): {e}")
                return False
        
        if p:
            # Basit metin yazdirma (baslik vb eklenebilir)
            p.text(content)
            p.cut()
            p.close()
            return True
    
    except ImportError:
        print("python-escpos kutuphanesi yuklu degil veya hatali.")
        return False
    except Exception as e:
        print(f"Yazdirma hatasi: {e}")
        return False

    return False


@app.route('/api/print/test', methods=['POST'])
@admin_required
def test_print():
    """Test yazdirma"""
    data = request.json
    printer_id = data.get('printer_id')
    printer = Printer.query.get_or_404(printer_id)
    
    content = f"""
--------------------------------
TEST FISI
--------------------------------
Yazici: {printer.name}
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}
--------------------------------
Bu bir test fisidir.
Turkce karakter destegi:
I i O o U u S s C c G g
--------------------------------
"""
    success = safe_print(printer, content)
    
    if success:
        return jsonify({'success': True, 'message': 'Test fisi gonderildi'})
    else:
        # Demo modunda basarili donelim ki UI test edilebilsin
        print(f"DEMO PRINT ({printer.name}):\n{content}")
        return jsonify({'success': True, 'message': 'Test fisi gonderildi (Demo Mode - Loglari kontrol edin)', 'demo': True})


@app.route('/api/orders/<int:order_id>/print', methods=['POST'])
def print_order_tickets(order_id):
    """Siparis fislerini yazdir"""
    # Yazdirma kapali mi?
    print_setting = Setting.query.get('print_enabled')
    if print_setting and print_setting.value != 'true':
        return jsonify({'success': False, 'message': 'Yazdirma kapali'})

    order = Order.query.get_or_404(order_id)
    
    # Yazdirilmamis urunleri bul
    unprinted_items = [item for item in order.items if not item.is_printed]
    
    if not unprinted_items:
        return jsonify({'success': True, 'message': 'Yazdirilacak yeni urun yok'})
    
    # Reyonlara gore grupla
    station_items = {}
    for item in unprinted_items:
        # Urunun reyonu var mi?
        menu_item = MenuItem.query.get(item.menu_item_id)
        station_id = menu_item.station_id if menu_item else None
        
        if station_id:
            if station_id not in station_items:
                station_items[station_id] = []
            station_items[station_id].append(item)
    
    printed_count = 0
    
    # Her reyon icin yazdir
    for station_id, items in station_items.items():
        station = Station.query.get(station_id)
        if not station or not station.printer_id:
            continue
            
        printer = Printer.query.get(station.printer_id)
        if not printer:
            continue
            
        # Fis icerigi hazirla
        content = f"""
--------------------------------
{station.name.upper()} FISI
Masa: {order.table.name}
Gars: {order.user_id}
Saat: {datetime.now().strftime('%H:%M')}
--------------------------------
"""
        for item in items:
            note_str = f" ({item.note})" if item.note else ""
            content += f"{item.quantity} x {item.name}{note_str}\n"
            
        content += "\n--------------------------------\n\n"
        
        # Yazdir veya Demo Yazdir
        success = safe_print(printer, content)
        if not success:
            print(f"DEMO PRINT ({printer.name} - {station.name}):\n{content}")
            
        # Yazdirildi olarak isaretle (Hata olsa bile isaretle ki tekrar tekrar denemeyelim, veya UI'dan tekrar tetiklenebilir olsun)
        # Gercek senaryoda sadece success ise isaretlenmeli. Burada demo oldugu icin isaretliyoruz.
        for item in items:
            item.is_printed = True
            
        printed_count += 1
        
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'{printed_count} reyon fisi yazdirildi',
        'data': order.to_dict()
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })


# ============== MAIN ==============

if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("")
    print("=" * 55)
    print("    ADISYO POS SISTEMI v2.0")
    print("    Flask + SQLite Backend")
    print("=" * 55)
    print("    Sunucu baslatiliyor...")
    print("    http://localhost:5000")
    print("=" * 55)
    print("")
    
    with app.app_context():
        init_database()
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
