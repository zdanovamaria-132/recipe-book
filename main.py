from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/name')
def name():
    return 'поиск по названиям'

@app.route('/ingredient')
def ingredient():
    return 'поиск по ингредиентам'

@app.route('/avtor')
def avtor():
    return 'авторизация'

@app.route('/regis')
def regis():
    return 'регистрация'

if __name__ == '__main__':
    app.run()