import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
# Определяем базу данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Директория для загружаемых изображений
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'imgs')

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    recipes = db.relationship('Recipe', backref='author', lazy=True)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description_food = db.Column(db.Text)
    description_recipe = db.Column(db.Text)
    # Ингредиенты хранятся как многострочный текст
    ingredient_id = db.Column(db.Text)
    category = db.Column(db.String(100))
    image_path = db.Column(db.String(200))

    # При удалении рецепта автоматически удаляются связанные рейтинги и записи избранного
    ratings = db.relationship('Rating', backref='recipe',
                              cascade="all, delete-orphan", lazy=True)
    favorites = db.relationship('Favorite', backref='recipe',
                                cascade="all, delete-orphan", lazy=True)


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id', ondelete='CASCADE'), nullable=False)


class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


@app.route('/')
@app.route('/main')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)


@app.route('/name', methods=['GET', 'POST'])
def name_route():
    if request.method == 'POST':
        search_query = request.form.get('search_query', '')
        recipes = Recipe.query.filter(Recipe.name.ilike(f'%{search_query}%')).all()
        results = [(r.id, r.name, r.description_food, r.description_recipe) for r in recipes]
        return render_template('name.html', results=results, search_query=search_query)
    return render_template('name.html', results=None, search_query="")


@app.route('/ingredient', methods=['GET', 'POST'])
def ingredient_route():
    ingredients = Ingredient.query.all()
    ingredients_list = [ing.name for ing in ingredients]
    if request.method == 'POST':
        selected_ingredients = request.form.getlist('ingredients')
        results = []
        if selected_ingredients:
            from sqlalchemy import or_
            conditions = [Recipe.ingredient_id.ilike(f'%{ing}%') for ing in selected_ingredients]
            recipes = Recipe.query.filter(or_(*conditions)).all()
            results = [(r.id, r.name, r.description_food, r.description_recipe) for r in recipes]
        return render_template('poisk-ingredient.html', ingredient=ingredients_list, results=results,
                               selected=selected_ingredients)
    return render_template('poisk-ingredient.html', ingredient=ingredients_list, results=None, selected=[])


@app.route('/avtor', methods=['GET', 'POST'])
def avtor():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            flash("Вы успешно авторизовались.", "success")
            return redirect(url_for('profile'))
        else:
            flash("Неверное имя пользователя или пароль.", "danger")
            return redirect(url_for('avtor'))
    return render_template('login.html')


@app.route('/regis', methods=['GET', 'POST'])
def regis():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Пользователь с таким именем уже существует.", "danger")
            return redirect(url_for('regis'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация завершена!", "success")
        return redirect(url_for('avtor'))
    return render_template('register.html')


@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Пользователь не найден. Пожалуйста, авторизуйтесь заново.", "danger")
            return redirect(url_for('avtor'))
        recipes = Recipe.query.filter_by(user_id=user.id).all()
        recipes_list = [{'id': r.id, 'name': r.name, 'description_food': r.description_food} for r in recipes]
        return render_template('profile.html', username=username, recipes=recipes_list)
    else:
        flash("Необходимо авторизоваться.", "warning")
        return redirect(url_for('avtor'))


@app.route('/favorite_recipe')
def favorite_recipe():
    if 'username' not in session:
        flash("Необходимо авторизоваться.", "warning")
        return redirect(url_for('avtor'))
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Пользователь не найден.", "danger")
        return redirect(url_for('avtor'))
    favorites = Favorite.query.filter_by(user_id=user.id).all()
    if not favorites:
        flash("Избранных рецептов нет.", "info")
        return redirect(url_for('profile'))
    recipe_ids = [fav.recipe_id for fav in favorites]
    recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
    recipes_list = [{'id': r.id, 'name': r.name, 'description': r.description_food} for r in recipes]
    return render_template('favorite_recipe.html', favorite_ingredients=recipes_list)


@app.route('/add_ingredient')
def add_ingredient():
    return render_template('add_recipe.html')


@app.route('/submit_recipe', methods=['POST'])
def submit_recipe():
    if 'username' not in session:
        flash("Войдите в систему, чтобы добавить рецепт.", "danger")
        return redirect(url_for('avtor'))

    recipe_name = request.form.get('recipeName')
    description_food = request.form.get('descriptionFood')
    description_recipe = request.form.get('recipeDescription')
    ingredients_id = request.form.get('ingredients')
    categor = request.form.get('category')
    username = session.get('username')

    # Обработка ингредиентов
    ingr_list = [line.strip() for line in ingredients_id.split('\n') if line.strip()]
    if not ingr_list:
        flash("Пожалуйста, введите ингредиенты.", "warning")
        return redirect(url_for('add_ingredient'))
    ingr_names = [line.split()[0].strip() for line in ingr_list if line.split()]
    if any(any(ch.isdigit() for ch in ing) for ing in ingr_names):
        flash("Вы ввели некорректные данные по ингредиентам.", "danger")
        return redirect(url_for('add_ingredient'))

    for ing in ingr_names:
        if not Ingredient.query.filter_by(name=ing).first():
            new_ing = Ingredient(name=ing)
            db.session.add(new_ing)

    # Работа с изображением (если загружено)
    img_file = request.files.get('photoUpload')
    img_path = None
    if img_file and img_file.filename != "":
        name_img = ''.join(str(ord(i)) for i in recipe_name)
        filename = secure_filename(name_img) + '.png'
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        img = Image.open(img_file)
        width, height = img.size
        if height > 400:
            new_height = 400
            new_width = int((new_height / height) * width)
            img = img.resize((new_width, new_height))
        img.save(img_path, format='PNG')

    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Ошибка: пользователь не найден.", "danger")
        return redirect(url_for('avtor'))

    new_recipe = Recipe(
        name=recipe_name,
        user_id=user.id,
        description_food=description_food,
        description_recipe=description_recipe,
        ingredient_id=ingredients_id,
        category=categor,
        image_path=img_path
    )
    db.session.add(new_recipe)
    db.session.commit()
    flash("Рецепт успешно добавлен!", "success")
    return redirect(url_for('profile'))


@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'username' not in session:
        flash("Необходимо авторизоваться.", "warning")
        return redirect(url_for('avtor'))
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Ошибка: пользователь не найден.", "danger")
        return redirect(url_for('avtor'))
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        flash("Рецепт не найден.", "danger")
        return redirect(url_for('profile'))
    if recipe.user_id != user.id:
        flash("Нет доступа к редактированию этого рецепта.", "danger")
        return redirect(url_for('profile'))

    if request.method == 'POST':
        updated_name = request.form.get('recipeName')
        updated_desc_food = request.form.get('descriptionFood')
        updated_desc_recipe = request.form.get('recipeDescription')
        updated_ingredients = request.form.get('ingredients')
        updated_category = request.form.get('category')
        recipe.name = updated_name
        recipe.description_food = updated_desc_food
        recipe.description_recipe = updated_desc_recipe
        recipe.ingredient_id = updated_ingredients
        recipe.category = updated_category
        db.session.commit()
        flash("Рецепт успешно обновлён!", "success")
        return redirect(url_for('profile'))

    recipe_data = [recipe.id, recipe.name, recipe.user_id, recipe.description_food,
                   recipe.description_recipe, recipe.ingredient_id, recipe.category]
    return render_template('edit_recipe.html', recipe=recipe_data)


@app.route('/recipe_watch')
def recipe_watch():
    username = session.get('username')
    recipe_id = request.args.get('recipe_id')
    if not recipe_id:
        flash("Рецепт не указан.", "warning")
        return redirect(url_for('main'))
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        flash("Рецепт не найден.", "danger")
        return redirect(url_for('main'))
    btn = False
    user_id = None
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            btn = True
            user_id = user.id
    avg_rating = db.session.query(db.func.avg(Rating.rating)).filter(Rating.recipe_id == recipe.id).scalar()
    is_favorite = False
    if user_id:
        fav = Favorite.query.filter_by(user_id=user_id, recipe_id=recipe.id).first()
        if fav:
            is_favorite = True
    recipe_data = {
        'id': recipe.id,
        'name': recipe.name,
        'description': recipe.description_food,
        'instructions': recipe.description_recipe.split('\n'),
        'ingredients': recipe.ingredient_id.split('\n'),
        'category': recipe.category,
        'avg_rating': avg_rating if avg_rating else 0,
        'favorite': is_favorite,
        'img': recipe.image_path if recipe.image_path else ''
    }
    return render_template('recipe-watch.html', username=username, recipe=recipe_data, btn=btn)


@app.route('/rate_recipe/<int:recipe_id>', methods=['POST'])
def rate_recipe(recipe_id):
    if 'username' not in session:
        flash("Необходимо авторизоваться для оценки.", "warning")
        return redirect(url_for('avtor'))
    try:
        rating_value = int(request.form.get('rating'))
        if rating_value < 1 or rating_value > 5:
            raise ValueError
    except:
        flash("Некорректное значение рейтинга.", "danger")
        return redirect(url_for('recipe_watch', recipe_id=recipe_id))
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Пользователь не найден.", "danger")
        return redirect(url_for('avtor'))
    rating = Rating.query.filter_by(user_id=user.id, recipe_id=recipe_id).first()
    if rating:
        rating.rating = rating_value
    else:
        rating = Rating(user_id=user.id, recipe_id=recipe_id, rating=rating_value)
        db.session.add(rating)
    db.session.commit()
    flash("Оценка успешно сохранена!", "success")
    return redirect(url_for('profile'))


@app.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
def toggle_favorite(recipe_id):
    if 'username' not in session:
        flash("Необходимо авторизоваться.", "warning")
        return redirect(url_for('avtor'))
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Пользователь не найден.", "danger")
        return redirect(url_for('avtor'))
    fav = Favorite.query.filter_by(user_id=user.id, recipe_id=recipe_id).first()
    if fav:
        db.session.delete(fav)
        flash("Рецепт удалён из избранного.", "info")
    else:
        new_fav = Favorite(user_id=user.id, recipe_id=recipe_id)
        db.session.add(new_fav)
        flash("Рецепт добавлен в избранное.", "success")
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'username' not in session:
        flash("Необходимо авторизоваться.", "warning")
        return redirect(url_for('avtor'))
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Ошибка: пользователь не найден.", "danger")
        return redirect(url_for('profile'))
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        flash("Рецепт не найден.", "danger")
        return redirect(url_for('profile'))
    if recipe.user_id != user.id:
        flash("Нет прав для удаления этого рецепта.", "danger")
        return redirect(url_for('profile'))

    for rating in recipe.ratings:
        db.session.delete(rating)
    for fav in recipe.favorites:
        db.session.delete(fav)

    db.session.delete(recipe)
    db.session.commit()
    flash("Рецепт успешно удалён.", "success")
    return redirect(url_for('profile'))


@app.route('/api/recipes', methods=['GET'])
def api_get_recipes():
    recipes = Recipe.query.all()
    output = []
    for r in recipes:
        output.append({
            'id': r.id,
            'name': r.name,
            'user_id': r.user_id,
            'description_food': r.description_food,
            'description_recipe': r.description_recipe,
            'ingredient_id': r.ingredient_id,
            'category': r.category,
            'image_path': r.image_path
        })
    return jsonify(output)


@app.route('/api/recipes/<int:id>', methods=['GET'])
def api_get_recipe(id):
    r = Recipe.query.get_or_404(id)
    output = {
        'id': r.id,
        'name': r.name,
        'user_id': r.user_id,
        'description_food': r.description_food,
        'description_recipe': r.description_recipe,
        'ingredient_id': r.ingredient_id,
        'category': r.category,
        'image_path': r.image_path
    }
    return jsonify(output)


@app.route('/api/recipes', methods=['POST'])
def api_create_recipe():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Нет данных'}), 400
    new_recipe = Recipe(
        name=data.get('name'),
        user_id=data.get('user_id'),
        description_food=data.get('description_food'),
        description_recipe=data.get('description_recipe'),
        ingredient_id=data.get('ingredient_id'),
        category=data.get('category'),
        image_path=data.get('image_path')
    )
    db.session.add(new_recipe)
    db.session.commit()
    return jsonify({
        'id': new_recipe.id,
        'name': new_recipe.name
    }), 201


@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаляем данные пользователя из сессии
    flash("Вы успешно вышли из профиля.", "info")  # Выводим flash-сообщение
    return redirect(url_for('index'))


@app.route('/api/recipes/<int:id>', methods=['PUT'])
def api_update_recipe(id):
    r = Recipe.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Нет данных'}), 400
    r.name = data.get('name', r.name)
    r.description_food = data.get('description_food', r.description_food)
    r.description_recipe = data.get('description_recipe', r.description_recipe)
    r.ingredient_id = data.get('ingredient_id', r.ingredient_id)
    r.category = data.get('category', r.category)
    r.image_path = data.get('image_path', r.image_path)
    db.session.commit()
    return jsonify({'id': r.id, 'name': r.name})


@app.route('/api/recipes/<int:id>', methods=['DELETE'])
def api_delete_recipe(id):
    r = Recipe.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'message': 'Recipe deleted'})


if __name__ == '__main__':
    with app.app_context():
        # Проверка внешних ключей для SQLite
        with db.engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
        db.create_all()
    app.run(debug=True)
