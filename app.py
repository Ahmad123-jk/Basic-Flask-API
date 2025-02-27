from flask import Flask, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask import request
import os

app = Flask(__name__)


#configuration de la connexion PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#initialisation de la base de données et de Marshmallow
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Modèle des tables
class Pokemon(db.Model):
    __tablename__ = 'pokemon'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(50))
    height = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    base_experience = db.Column(db.Integer)
    order = db.Column(db.Integer)
    is_default = db.Column(db.Boolean)
    species_id = db.Column(db.Integer, db.ForeignKey('pokemon_species.id'))
    types = db.relationship("PokemonType", backref="pokemon", cascade="all, delete-orphan")

class PokemonSpecies(db.Model):
    __tablename__ = 'pokemon_species'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(50))
    generation_id = db.Column(db.Integer)
    evolves_from_species_id = db.Column(db.Integer, db.ForeignKey('pokemon_species.id'))
    evolution_chain_id = db.Column(db.Integer)
    color_id = db.Column(db.Integer, db.ForeignKey('pokemon_colors.id'))
    shape_id = db.Column(db.Integer, db.ForeignKey('pokemon_shapes.id'))
    habitat_id = db.Column(db.Integer)
    gender_rate = db.Column(db.Integer)
    capture_rate = db.Column(db.Integer)
    base_happiness = db.Column(db.Integer)
    is_baby = db.Column(db.Boolean)
    hatch_counter = db.Column(db.Integer)
    has_gender_differences = db.Column(db.Boolean)
    growth_rate_id = db.Column(db.Integer)
    forms_switchable = db.Column(db.Boolean)
    order = db.Column(db.Integer)
    conquest_order = db.Column(db.Integer)

    color = db.relationship("PokemonColor", lazy='joined')
    shape = db.relationship("PokemonShape", lazy='joined')

class PokemonColor(db.Model):
    __tablename__ = 'pokemon_colors'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(50))

class PokemonShape(db.Model):
    __tablename__ = 'pokemon_shapes'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(50))

class PokemonType(db.Model):
    __tablename__ = 'pokemon_types'
    id = db.Column(db.Integer, db.ForeignKey('pokemon.id'), primary_key=True)
    type_id = db.Column(db.Integer, db.ForeignKey('types.id'), primary_key=True)
    slot = db.Column(db.Integer)

class Type(db.Model):
    __tablename__ = 'types'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(50))
    generation_id = db.Column(db.Integer)
    damage_class_id = db.Column(db.Integer)


#schémas pour la sérialisation JSON
class PokemonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Pokemon

class PokemonSpeciesSchema(ma.SQLAlchemyAutoSchema):
    evolves_from_species_id = ma.Function(lambda obj: obj.evolves_from_species_id if obj and obj.evolves_from_species_id else None)
    color = ma.Function(lambda obj: obj.color.identifier if obj and obj.color else None)
    shape_id = ma.Function(lambda obj: obj.shape.identifier if obj and obj.shape else None)

    class Meta:
        model = PokemonSpecies

pokemon_schema = PokemonSchema()
pokemon_species_schema = PokemonSpeciesSchema()

@app.route("/")
def home():
    return {
        "message": "Welcome to the Pokemon API: /api/pokemons"
    }

@app.route("/api/pokemons", methods=["GET"])
def get_pokemons():
    try:
        page = request.args.get('page', 1, type=int)  # Page par défaut = 1
        per_page = request.args.get('per_page', 10, type=int)  # Nombre d'éléments par page (par défaut 10)

        query = db.session.query(Pokemon, PokemonSpecies).outerjoin(PokemonSpecies, Pokemon.id == PokemonSpecies.id)
        total = query.count()  # Nombre total d'éléments

        paginated_pokemons = query.paginate(page=page, per_page=per_page, error_out=False)  # Pagination

        # Construction des liens pour naviguer entre les pages
        next_url = url_for('get_pokemons', page=paginated_pokemons.next_num,
                           per_page=per_page) if paginated_pokemons.has_next else None
        prev_url = url_for('get_pokemons', page=paginated_pokemons.prev_num,
                           per_page=per_page) if paginated_pokemons.has_prev else None

        # Sérialisation des résultats
        results = [
            pokemon_schema.dump(p[0]) | pokemon_species_schema.dump(p[1])
            for p in paginated_pokemons.items
        ]

        return jsonify({
            "total": total,
            "page": page,
            "prev_page": prev_url,
            "next_page": next_url,
            "per_page": per_page,
            "data": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/pokemons/<int:id>", methods=["GET"])
def get_pokemon(id):
    try:
        pokemon = db.session.query(Pokemon, PokemonSpecies).outerjoin(PokemonSpecies,
                                                                      Pokemon.species_id == PokemonSpecies.id).filter(
            Pokemon.id == id).first_or_404()

        pokemon_data = pokemon_schema.dump(pokemon[0])  # Données de la table `pokemon`
        species_data = pokemon_species_schema.dump(pokemon[1]) if pokemon[1] else {}

        species_data["identifier"] = pokemon_data["identifier"]
        species_data["order"] = pokemon_data["order"]

        return jsonify({**pokemon_data, **species_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pokemons/<int:id>", methods=["PUT"])
def update_pokemon(id):
    try:
        data = request.json

        # ID non modifiable
        if "id" in data:
            del data["id"]

        if not data:
            return jsonify({"message": "No input data provided"}), 400

        # Construction du dictionnaire des champs à mettre à jour
        update_data = {key: data[key] for key in data if key in Pokemon.__table__.columns and data[key] is not None}

        if not update_data:
            return jsonify({"message": "No data changed"}), 400

        # Mise à jour en une seule requête SQL
        db.session.query(Pokemon).filter_by(id=id).update(update_data)
        db.session.commit()
        db.session.expire_all()  # Forcer le rafraîchissement des données

        return jsonify({"message": "Pokemon updated successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/pokemons/", methods=["POST"])
def add_pokemon():
    try:
        data = request.json

        if not data:
            return jsonify({"message": "No input data provided"}), 400

        species_id = data.get("evolves_from_species_id")
        species = None
        if species_id is None:
            species = PokemonSpecies(
                identifier=data["identifier"],
                generation_id=data["generation_id"],
                evolves_from_species_id=data["evolves_from_species_id"],
                evolution_chain_id=data["evolution_chain_id"],
                color_id=data["color_id"],
                shape_id=data["shape_id"],
                habitat_id=data["habitat_id"],
                gender_rate=data["gender_rate"],
                capture_rate=data["capture_rate"],
                base_happiness=data["base_happiness"],
                is_baby=data["is_baby"],
                hatch_counter=data["hatch_counter"],
                has_gender_differences=data["has_gender_differences"],
                growth_rate_id=data["growth_rate_id"],
                forms_switchable=data["forms_switchable"],
                order=data["order"],
                conquest_order=data["conquest_order"]
            )
            db.session.add(species)
            db.session.flush()
            species_id = species.id

        new_pokemon = Pokemon(
            identifier=data["identifier"],
            species_id=species_id,
            height=data["height"],
            weight=data["weight"],
            base_experience=data["base_experience"],
            order=data["order"],
            is_default=data["is_default"]
        )

        db.session.add(new_pokemon)
        db.session.commit()

        json_data = pokemon_schema.dump(new_pokemon) | pokemon_species_schema.dump(species)
        return jsonify({"message": "Pokemon added successfully!", "pokemon": json_data}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/pokemons/<int:id>", methods=["DELETE"])
def delete_pokemon(id):
    pokemon = Pokemon.query.get(id)
    if not pokemon:
        return jsonify({"message": "Pokemon not found"}), 404

    db.session.delete(pokemon)
    db.session.commit()

    return jsonify({"message": "Pokemon deleted successfully"})

if __name__ == '__main__':
    app.run(debug=True)
