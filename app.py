from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask import request

app = Flask(__name__)


#configuration de la connexion PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#initialisation de la base de données et de Marshmallow
db = SQLAlchemy(app)
ma = Marshmallow(app)

#Modèle POkemon basé sur la table existante
class Pokemon(db.Model):
    __tablename__ = 'pokemon'

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(50))
    height = db.Column(db.Integer)
    weight = db.Column(db.Integer)


# Schéma pour la sérialisation JSON
class PokemonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Pokemon

pokemon_schema = PokemonSchema()
pokemons_schema = PokemonSchema(many=True)

@app.route("/")
def hello_world():
    return {
        "message": "Hello, World!"
    }

#route pour récupérer tous les pokemons
@app.route("/api/pokemon", methods=["GET"])
def get_pokemons():
    page = request.args.get('page', 1, type=int) #page de la requête
    per_page = request.args.get('per_page', 10, type=int) #nombre de pokemons par page

    pokemons = Pokemon.query.paginate(page=page, per_page=per_page, error_out=False)
    # Construction des liens pour naviguer entre les pages
    next_url = f'/api/pokemon?page={pokemons.next_num}&per_page={per_page}' if pokemons.has_next else None
    prev_url = f'/api/pokemon?page={pokemons.prev_num}&per_page={per_page}' if pokemons.has_prev else None

    return jsonify(
        {
            "pokemons": pokemons_schema.dump(pokemons.items),
            "total": pokemons.total,
            "pages": pokemons.pages,
            "current_page": pokemons.page,
            "next_page": next_url,
            "prev_page": prev_url
        }
    )

#route pour récupérer un pokemon par son id
@app.route("/api/pokemon/<int:id>", methods=["GET"])
def get_pokemon(id):
    pokemon = Pokemon.query.get_or_404(id) #récupération du pokemon par son id ou 404 si non trouvé
    return jsonify(pokemon_schema.dump(pokemon))


if __name__ == '__main__':
    app.run(debug=True)