from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Настройки хранения сессии
app.config['SESSION_TYPE'] = 'filesystem'  # Или 'sqlalchemy' для хранения в БД
Session(app)


# Настройка базы данных
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    username = session.get('username')  # Проверяем, есть ли пользователь в сессии
    if username:
        return render_template('index.html', username=username)  # Для авторизованных
    return render_template('index.html')  # Для неавторизованных


@app.route('/name')
def name():
    return 'поиск по названиям'


@app.route('/ingredient')
def ingredient():
    return 'поиск по ингредиентам'


@app.route('/avtor', methods=['GET', 'POST'])
def avtor():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = username  # Сохраняем имя пользователя в сессии
            return redirect(url_for('profile'))
        else:
            return 'Неверное имя пользователя или пароль.'
    return render_template('login.html')


@app.route('/regis', methods=['GET', 'POST'])
def regis():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return 'Регистрация успешна!'
    return render_template('register.html')


@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        return render_template('profile.html', username=username)
    else:
        return redirect(url_for('avtor'))


@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаление данных из сессии
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
