import random
import re
import numpy as np
from collections import Counter
from math import log
from flask_restful import Resource
from flask import request
import polars as pl
from dotenv import load_dotenv
import os

load_dotenv()
SPRING_REQUEST_URL = os.getenv("SPRING_URL")  # 스프링 요청 도메인


def preprocess(text: str):
    """
    문장 데이터 전처리
    :param text: 문장
    :return: 토큰화된 문장
    """
    text = text.lower()
    text = re.sub(r"[^a-z\s]", "", text)
    tokens = text.split()
    # 의미 분석에서 큰 의미가 없는 단어 제거
    stop_words = {
        "the", "is", "a", "an", "and", "to", "of", "for", "in", "on", "with", "at", "from", "by"
    }
    tokens = [t for t in tokens if t not in stop_words]
    return tokens


def compute_tfidf(corpus):
    """
    TF-IDF 벡터 생성
    :param corpus: 문장 리스트
    :return: TF-IDF 행렬 (numpy.ndarray)
    """
    # 모든 문서 토큰화
    tokenized_docs = [preprocess(doc) for doc in corpus]
    vocab = sorted(set(word for doc in tokenized_docs for word in doc))
    vocab_index = {word: idx for idx, word in enumerate(vocab)}

    N = len(tokenized_docs)
    V = len(vocab)
    tfidf = np.zeros((N, V))

    # DF 계산
    df = Counter(word for doc in tokenized_docs for word in set(doc))

    # TF-IDF 계산
    for i, doc in enumerate(tokenized_docs):
        tf = Counter(doc)
        for word, count in tf.items():
            j = vocab_index[word]
            tf_val = count / len(doc)
            idf_val = log((N + 1) / (df[word] + 1)) + 1  # sklearn의 smooth IDF 방식
            tfidf[i, j] = tf_val * idf_val

    # L2 정규화
    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    tfidf = np.divide(tfidf, norms, where=norms != 0)

    return tfidf, vocab


def cosine_similarity_matrix(tfidf_matrix):
    """
    코사인 유사도 계산
    :param tfidf_matrix: tf-idf 행렬
    :return: cosine_similarity 행렬
    """
    return np.dot(tfidf_matrix, tfidf_matrix.T)


# csv 파일 읽기
df = pl.read_csv('./api/data/megaGymDataset_.csv', encoding='ISO-8859-1')
# 문자열 형 변환
df = df.with_columns(df["Desc"].cast(pl.Utf8))

# 텍스트 리스트로 추출
corpus = df["Desc"].to_list()

# TF-IDF + cosine 유사도 계산
tfidf_matrix, vocab = compute_tfidf(corpus)
cos_sim = cosine_similarity_matrix(tfidf_matrix)


class RecommendExercise(Resource):
    def post(self):
        # 입력 데이터 수신
        user_id = request.json.get('id')  # 사용자 아이디
        message = request.json.get('message', '').lower()  # 부위
        goal = request.json.get('goal', '').lower()  # 목표
        level = request.json.get('level', '').lower()  # 난이도

        print(f"[INFO] user_id={user_id}, part={message}, goal={goal}, level={level}")

        # Bodypart 매핑
        bodyparts = self.map_bodypart(message)
        selected_bodypart = random.choice(bodyparts)
        print(f"[INFO] 선택된 부위: {selected_bodypart}")

        # exercise_index = df[df['BodyPart'] == selected_bodypart].index[0]

        exercise_index = df.filter(pl.col("BodyPart") == selected_bodypart).row(0)[0]

        # TF-IDF + cosine 기반 유사 운동 추천
        recommended_exercises = self.recommend(exercise_index, goal, level)
        result_string = ', '.join(recommended_exercises)
        print(f"[INFO] 추천 운동 목록: {recommended_exercises}")

        # Spring Boot API 호출 → DB 저장

    def recommend(self, exercise_index, goal, level):
        # 유사도 계산
        index_cosSim = list(enumerate(cos_sim[exercise_index]))
        sorted_sim = sorted(index_cosSim, key=lambda x: x[1], reverse=True)

        # 상위 10개 후보
        # top_indices = [idx for idx, _ in sorted_sim[1:15]]
        # candidates = df.take(top_indices)

        # goal, level 값 반영
        def adjust_score(row, base_score):
            """
            가중치 값 계산
            :param row: 데이터 한 행
            :param base_score: 기본 점수
            :return: goal, level 값 반영 결과
            """
            score = base_score
            print("!!!!! desc 값 확인", row['Desc'])
            desc = row['Desc'][0].lower()
            difficulty = row['Difficulty'][0].lower()

            # goal 관련 가중치
            if goal == 'muscle_gain' and any(k in desc for k in ['strength', 'mass', 'build']):
                score += 0.1
            elif goal == 'fat_loss' and any(k in desc for k in ['burn', 'cardio', 'fat']):
                score += 0.1
            elif goal == 'rehabilitation' and any(k in desc for k in ['stretch', 'rehab', 'recovery']):
                score += 0.1

            # level 관련 가중치
            if level == 'Beginner' and difficulty in ['beginner', 'easy']:
                score += 0.1
            elif level == 'Expert' and difficulty in ['hard', 'expert']:
                score += 0.1
            elif level == 'Intermediate' and difficulty in ['middle', 'intermediate']:
                score += 0.1

            return score

        # 각 후보
        scored = []
        for idx, base_score in sorted_sim[1:15]:
            row = (
                df.with_row_count("row_nr")
                .filter(pl.col("row_nr") == idx)
                .drop("row_nr")
            )
            scored.append((idx, adjust_score(row, base_score)))

        # 점수 순으로 정렬 후 상위 3개 선택
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)[:3]
        top3_indices = [idx for idx, _ in scored_sorted]
        titles = (
            df
            .with_row_count("row_nr")
            .filter(pl.col("row_nr").is_in(top3_indices))
            .select("Title")
            .to_series()
            .to_list()
        )
        return titles

    def map_bodypart(self, message):
        """
        부위 매핑
        :param message: 사용자가 선택한 부위
        :return: 부위에 따른 하위 카테고리 랜덤 반환
        """
        if message == 'shoulders':
            return ['Shoulders', 'Traps']
        elif message == 'arms':
            return ['Biceps', 'Forearms', 'Triceps']
        elif message == 'legs':
            return ['Calves', 'Adductors', 'Quadriceps', 'Hamstrings']
        elif message == 'back':
            return ['Lats', 'Lower Back', 'Middle Back']
        elif message == 'chest':
            return ['Chest']
        elif message == 'random':
            return df['BodyPart'].unique().tolist()
        else:
            return [message]
