import os
import random

from flask_restful import Resource
import polars as pl
import requests
from flask import request
import numpy as np
from api.models import db, Food
from flask import Flask, request, jsonify

class NutrientRecommender(Resource):
    def post(self):
        user_data = request.json
        familiar_ingredients = user_data.get("familiar_ingredients", [])
        foods = Food.query.all()
        print(f'가져온 음식 리스트: {len(foods)}')
        scored_foods = []

        for food in foods:
            nutrient_score = calculate_nutrient_score(user_data, food)
            ingredient_score = calculate_ingredient_score(familiar_ingredients, food)
            # 낮을수록 좋은 nutrient score를 뒤집어서 higher is better 형태로 변경
            final_score = (1 / (nutrient_score + 1)) + ingredient_score

            scored_foods.append({
                "id": food.custom_code,
                "foodname": food.foodname,
                "nutrient_score": nutrient_score,
                "ingredient_score": ingredient_score,
                "final_score": final_score
            })

            # final_score 기준으로 내림차순 정렬 (높을수록 추천)
            scored_foods = sorted(scored_foods, key=lambda x: x["final_score"], reverse=True)
        print(scored_foods)
        return jsonify(scored_foods[:10])
def calculate_nutrient_score(user, food):
    """
    사용자의 현재 섭취 상태와 food의 영양의 차이를 기반으로 점수를 계산.
    값이 낮을수록 더 좋은 음식.
    """

    # 이상적 목표량 설정 (기본값, 실제 서비스에서는 개인별 맞춤으로 변경 가능)
    ideal = {
        "carb": 250,
        "protein": 70,
        "fat": 60,
        "sodium": 1500,
        "chol": 300
    }

    # 부족/과다 가중치 설정
    weights = {
        "carb": 1.2,
        "protein": 1.0,
        "fat": 1.5,
        "sodium": 2.0,
        "chol": 1.3
    }

    score = (
            weights["carb"] * abs((ideal["carb"] - user["carb"]) - food.carbohydrate) +
            weights["protein"] * abs((ideal["protein"] - user["protein"]) - food.protein) +
            weights["fat"] * abs((ideal["fat"] - user["fat"]) - food.fat) +
            weights["sodium"] * abs((ideal["sodium"] - user["sodium"]) - food.sodium) +
            weights["chol"] * abs((ideal["chol"] - user["chol"]) - food.cholesterol)
    )

    return score


def calculate_ingredient_score(familiar_ingredients, food):
    """
    사용자가 자주 먹는 재료 또는 선호 재료 기반 점수.
    """
    if not familiar_ingredients:
        return 0

    food_ingredients = [i.ingredient for i in food.ingredients]

    matched = len(set(food_ingredients) & set(familiar_ingredients))
    return matched / max(len(food_ingredients), 1)  # 0~1 사이 값
