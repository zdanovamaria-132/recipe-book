from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import sqlite3
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Настройки хранения сессии
app.config['SESSION_TYPE'] = 'filesystem'  # Или 'sqlalchemy' для хранения в БД
Session(app)

app.config['UPLOAD_FOLDER'] = 'uploads/'


# Настройка базы данных
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Создание таблицы рецептов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            id_user INTEGER NOT NULL,
            description_food TEXT,
            description_recipe TEXT,
            ingredient_id TEXT,
            category TEXT,
            FOREIGN KEY (id_user) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        )
    ''')
    conn.commit()
    conn.close()


init_db()


@app.route('/')
@app.route('/main')
def index():
    username = session.get('username')
    if username:
        return render_template('index.html', username=username)  # Для авторизованных
    return render_template('index.html')  # Для неавторизованных


@app.route('/name', methods=['GET', 'POST'])
def name():
    if request.method == 'POST':
        search_query = request.form.get('search_query', '')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description_food, description_recipe FROM recipes WHERE name LIKE ?",
            (f"%{search_query}%",)
        )
        results = cursor.fetchall()
        conn.close()
        return render_template('name.html', results=results, search_query=search_query)

    return render_template('name.html', results=None, search_query="")


@app.route('/ingredient', methods=['GET', 'POST'])
def ingredient():
    ingredients_list = ['Помидоры', 'Огурцы', 'Лук', 'Перец']

    if request.method == 'POST':
        selected_ingredients = request.form.getlist('ingredients')


        results = []
        if selected_ingredients:
            conditions = []
            params = []
            for ing in selected_ingredients:
                conditions.append("ingredient_id LIKE ?")
                params.append(f"%{ing}%")
            query = "SELECT id, name, description_food, description_recipe FROM recipes WHERE " + " OR ".join(
                conditions)

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
        return render_template(
            'poisk-ingredient.html',
            ingredient=ingredients_list,
            results=results,
            selected=selected_ingredients
        )

    return render_template('poisk-ingredient.html', ingredient=ingredients_list, results=None, selected=[])


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
            session['username'] = username
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
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            return redirect(url_for('avtor'))
        user_id = user_row[0]

        cursor.execute('''
            SELECT id, name, description_food, description_recipe, ingredient_id, category 
            FROM recipes 
            WHERE id_user = ?
        ''', (user_id,))
        recipes_raw = cursor.fetchall()
        recipes = []
        for rec in recipes_raw:
            recipe_id, name, desc_food, desc_recipe, ingredients, category = rec
            cursor.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (recipe_id,))
            avg_rating = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM favorites WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
            is_favorite = bool(cursor.fetchone())
            recipes.append({
                'id': recipe_id,
                'name': name,
                'description_food': desc_food,
                'description_recipe': desc_recipe,
                'ingredients': ingredients,
                'category': category,
                'avg_rating': avg_rating,
                'favorite': is_favorite
            })
        conn.close()
        return render_template('profile.html', username=username, recipes=recipes)
    else:
        return redirect(url_for('avtor'))


@app.route('/add_ingredient')
def add_ingredient():
    return render_template('add_recipe.html')


@app.route('/submit_recipe', methods=['POST'])
def submit_recipe():
    if 'username' not in session:
        return redirect(url_for('avtor'))

    recipe_name = request.form['recipeName']
    description_food = request.form['descriptionFood']
    description_recipe = request.form['recipeDescription']
    ingredients_id = request.form['ingredients']
    username = session['username']

    # Работа с файлом:
    img_file = request.files.get('photoUpload')
    img_path = None
    if img_file and img_file.filename != "":
        filename = secure_filename(img_file.filename)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img_file.save(img_path)

    print("Название рецепта:", recipe_name)
    print("Описание блюда:", description_food)
    print("Инструкции:", description_recipe)
    print("Ингредиенты:", ingredients_id)
    print('username:', username)

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


@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'username' not in session:
        return redirect(url_for('avtor'))

    username = session['username']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return "Ошибка: пользователь не найден"
    user_id = user_row[0]

    cursor.execute("SELECT id_user FROM recipes WHERE id = ?", (recipe_id,))
    owner = cursor.fetchone()
    if not owner:
        conn.close()
        return "Рецепт не найден"
    if owner[0] != user_id:
        conn.close()
        return "Нет прав для удаления этого рецепта"

    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('profile'))


@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'username' not in session:
        return redirect(url_for('avtor'))

    username = session['username']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Получаем id пользователя
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return "Ошибка: пользователь не найден"
    user_id = user_row[0]

    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        conn.close()
        return "Рецепт не найден"

    if recipe[2] != user_id:
        conn.close()
        return "Нет доступа к редактированию этого рецепта"

    if request.method == 'POST':
        updated_name = request.form['recipeName']
        updated_desc_food = request.form['descriptionFood']
        updated_desc_recipe = request.form['recipeDescription']
        updated_ingredients = request.form['ingredients']

        cursor.execute("""
            UPDATE recipes
            SET name = ?, description_food = ?, description_recipe = ?, ingredient_id = ?
            WHERE id = ?
        """, (updated_name, updated_desc_food, updated_desc_recipe, updated_ingredients, recipe_id))
        conn.commit()
        conn.close()
        return redirect(url_for('profile'))

    conn.close()
    return render_template('edit_recipe.html', recipe=recipe)


@app.route('/rate_recipe/<int:recipe_id>', methods=['POST'])
def rate_recipe(recipe_id):
    if 'username' not in session:
        return redirect(url_for('avtor'))

    rating = request.form.get('rating')
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        return "Некорректное значение рейтинга", 400

    username = session['username']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return "Пользователь не найден", 400
    user_id = user_row[0]

    cursor.execute("SELECT id FROM ratings WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE ratings SET rating = ? WHERE id = ?", (rating, existing[0]))
    else:
        cursor.execute("INSERT INTO ratings (user_id, recipe_id, rating) VALUES (?, ?, ?)",
                       (user_id, recipe_id, rating))
    conn.commit()
    conn.close()
    return redirect(url_for('profile'))


@app.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
def toggle_favorite(recipe_id):
    if 'username' not in session:
        return redirect(url_for('avtor'))

    username = session['username']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return "Пользователь не найден", 400
    user_id = user_row[0]

    cursor.execute("SELECT id FROM favorites WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
    fav = cursor.fetchone()
    if fav:
        cursor.execute("DELETE FROM favorites WHERE id = ?", (fav[0],))
    else:
        cursor.execute("INSERT INTO favorites (user_id, recipe_id) VALUES (?, ?)", (user_id, recipe_id))
    conn.commit()
    conn.close()
    return redirect(url_for('profile'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
