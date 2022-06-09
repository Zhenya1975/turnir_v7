from flask import Flask, render_template, request, flash
from extensions import extensions
from routes.routes import home

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://evgenijzupanik:123456@localhost:5432/flask_db4'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'secret string'

db = extensions.db
migrate = extensions.migrate

db.init_app(app)
migrate.init_app(app, db, render_as_batch=True)

app.register_blueprint(home)

if __name__ == '__main__':
    app.run(debug=True)
