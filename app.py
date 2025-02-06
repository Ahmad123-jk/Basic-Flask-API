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

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(100), nullable=False)
    species_id = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    base_experience = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    is_default = db.Column(db.Boolean, nullable=False)


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

#route pour modifier les données d'un pokemon récupéré par son id
@app.route("/api/pokemon/<int:id>",methods=["PUT"])
def update_pokemon(id):
    pokemon = Pokemon.query.get_or_404(id) # Vérifie si le Pokémon existe sinon retourne 404

    #récupérer les données de la requête de l'utilisateur
    data = request.json
    print(data["identifier"])

    if not data:
        return jsonify({"message": "No input data provided"}), 400

    modified = False

    #vérifier si les données sont présentes avant de les modifier
    if "identifier" in data and data["identifier"] != pokemon.identifier:
        pokemon.identifier = data["identifier"]
        modified = True

    if "height" in data and data["height"] != pokemon.height:
        pokemon.height = data["height"]
        modified = True

    if "weight" in data and data["weight"] != pokemon.weight:
        pokemon.weight = data["weight"]
        modified = True

    if not modified:
        return jsonify({"message": "No data changed"}), 400

    db.session.commit() #sauvegarde des modifications dans la base de données

    return jsonify({"message": "Pokemon updated successfully", "pokemon": pokemon_schema.dump(pokemon)})


@app.route("api/pokemon/", methods=["POST"])
def add_pokemon():
    try:
        data = request.json

        # Validate required fields
        required_fields = ["id", "identifier", "species_id", "height", "weight", "base_experience", "order",
                           "is_default"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        new_pokemon = Pokemon(
            id=data["id"],
            identifier=data["identifier"],
            species_id=data["species_id"],
            height=data["height"],
            weight=data["weight"],
            base_experience=data["base_experience"],
            order=data["order"],
            is_default=data["is_default"]
        )

        db.session.add(new_pokemon)
        db.session.commit()

        return jsonify({"message": "Pokemon added successfully!", "pokemon": data}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)