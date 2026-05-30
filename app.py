# from flask import Flask, render_template, request, redirect
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
#
# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newflask.db'
# db = SQLAlchemy(app)
#
# migrate = Migrate(app, db)
#
# class Post(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(300), nullable=True)
#     login = db.Column(db.String, nullable=False)
#     password = db.Column(db.String(300))
#     status = db.Column(db.String(50), default='user')
#
#
# @app.route ("/shop")
# def shop():
#     return render_template('shop.html')
#
#
# @app.route("/login", methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         login_input = request.form['login']
#         password_input = request.form['password']
#
#         # Ищем пользователя в БД с таким логином и паролем
#         user = Post.query.filter_by(login=login_input, password=password_input).first()
#
#         if user:
#             # Если нашли - отправляем на следующую страницу
#             return redirect('/shop')
#         else:
#             # Если не нашли - показываем ошибку
#             return 'Неверный логин или пароль'
#     else:
#         return render_template('login.html')
#
# @app.route("/" , methods=['POST', 'GET'])
# def index():
#     if request.method == 'POST':
#         name = request.form['name']
#         login = request.form['login']
#         password = request.form['password']
#         status = request.form.get('status', 'user')
#
#         post = Post(name=name, login=login, password=password, status=status)
#
#         try:
#             db.session.add(post)
#             db.session.commit()
#             return redirect('/login')
#         except:
#             return 'при добавлении произошла ошибка'
#
#         return redirect('shop.html')
#     else:
#         return render_template('register.html')
#
#
# if __name__ == '__main__':
#     app.run(debug=True)
#


from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
import bcrypt
from datetime import datetime
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newflask.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SESSION_TYPE'] = 'filesystem'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
Session(app)

# ======================= МОДЕЛИ =======================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(300), nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='user')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'image_url': self.image_url,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ======================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =======================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def validate_email(email):
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email) is not None


# ======================= API ЭНДПОИНТЫ =======================
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    email = data.get('email', '').strip()
    name = data.get('name', '').strip()
    password = data.get('password', '')

    # Валидация
    errors = []
    if not email:
        errors.append('Email is required')
    elif not validate_email(email):
        errors.append('Invalid email format')
    if not name:
        errors.append('Name is required')
    if not password:
        errors.append('Password is required')
    elif len(password) < 6:
        errors.append('Password must be at least 6 characters')

    if errors:
        return jsonify({'errors': errors}), 400

    # Проверка на существующего пользователя
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    # Создание пользователя
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_status'] = user.status

    return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200


@app.route('/api/auth/me', methods=['GET'])
@login_required
def api_me():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200


# ======================= CRUD ДЛЯ ТОВАРОВ =======================
@app.route('/api/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([item.to_dict() for item in items]), 200


@app.route('/api/items', methods=['POST'])
@login_required
def create_item():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    name = data.get('name', '').strip()
    price = data.get('price')
    description = data.get('description', '')
    image_url = data.get('image_url', '')

    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if not price or not isinstance(price, (int, float)) or price <= 0:
        return jsonify({'error': 'Valid price is required'}), 400

    item = Item(
        name=name,
        price=price,
        description=description,
        image_url=image_url,
        created_by=session['user_id']
    )
    db.session.add(item)
    db.session.commit()

    return jsonify(item.to_dict()), 201


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    item = Item.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    # Только создатель или админ могут удалить
    if item.created_by != session['user_id'] and session.get('user_status') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 200


# ======================= СТРАНИЦЫ (ФРОНТЕНД) =======================
@app.route('/auth/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('profile_page'))
    return render_template('login.html')


@app.route('/auth/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('profile_page'))
    return render_template('register.html')


@app.route('/profile')
@login_required
def profile_page():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@app.route('/dashboard')
@login_required
def dashboard():
    items = Item.query.filter_by(created_by=session['user_id']).all()
    return render_template('dashboard.html', items=items)


@app.route('/shop')
@login_required
def shop():
    return render_template('shop.html')


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile_page'))
    return redirect(url_for('login_page'))

# ======================= ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ =======================
@app.route('/login')
def login():
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)