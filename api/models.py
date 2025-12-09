from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Food(db.Model):
    __tablename__ = 'foodlist'

    custom_code = db.Column(db.Integer)
    foodname = db.Column(db.String(255), primary_key=True)
    calory = db.Column(db.Float)
    carbohydrate = db.Column(db.Float)
    protein = db.Column(db.Float)
    fat = db.Column(db.Float)
    sodium = db.Column(db.Float)
    cholesterol = db.Column(db.Float)

    ingredients = db.relationship(
        "RecipeIngredient",
        primaryjoin="Food.custom_code == RecipeIngredient.recipecode",
        foreign_keys="RecipeIngredient.recipecode",
        lazy="select"
    )


class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    ingredient = db.Column(db.String(100))
    recipecode = db.Column(db.Integer)
    ri_amount = db.Column(db.String(50))
    ri_purchase_link = db.Column(db.String(200))
