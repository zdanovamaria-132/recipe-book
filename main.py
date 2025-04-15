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
@app.route('/main')
def index():
    username = session.get('username')  # Проверяем, есть ли пользователь в сессии
    if username:
        return render_template('index.html', username=username)  # Для авторизованных
    return render_template('index.html')  # Для неавторизованных


@app.route('/name')
def name():
    return 'поиск по названиям'


@app.route('/ingredient', methods=['GET', 'POST'])
def ingredient():
    ingredients = ['Помидоры', 'Огурцы', 'Лук', 'Перец']  # Пример списка ингредиентов
    if request.method == 'POST':
        selected_ingredients = request.form.getlist('ingredients')
        print('вы выбрали:', selected_ingredients)  # Здесь вы можете обработать выбранные ингредиенты
        # После обработки, перенаправляем на главную страницу
        return redirect(url_for('index'))  # Перенаправление на главный маршрут
    return render_template('poisk-ingredient.html', ingredient=ingredients)


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


@app.route('/add_ingredient')
def add_ingredient():
    return render_template('add_recipe.html')


@app.route('/submit_recipe', methods=['POST'])
def submit_recipe():
    if 'username' not in session:
        return redirect(url_for('avtor'))  # Если пользователь не авторизован, переходим на страницу авторизации

    recipe_name = request.form['recipeName']
    description_food = request.form['descriptionFood']
    description_recipe = request.form['recipeDescription']
    ingredients_id = request.form[
        'ingredients']  # Предполагается, что это строка с ID ингредиентов, но пока тут просто строка
    img = request.form['photoUpload']
    username = session['username']

    # Вывод данных в консоль
    print("Название рецепта:", recipe_name)
    print("Описание блюда:", description_food)
    print("Инструкции:", description_recipe)
    print("Ингредиенты:", ingredients_id)
    print('username:', username)

    # Получим id пользователя из базы данных по имени пользователя
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    user_id = cursor.fetchone()

    if user_id:
        user_id = user_id[0]  # Получаем id пользователя
        cursor.execute('''
            INSERT INTO recipes (name, id_user, description_food, description_recipe, ingredient_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (recipe_name, user_id, description_food, description_recipe, ingredients_id))

        conn.commit()
        conn.close()
        return "Рецепт успешно добавлен!"
    else:
        conn.close()
        return "Ошибка: Пользователь не найден."


@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаление данных из сессии
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
