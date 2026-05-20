import requests
import pandas as pd
import time
import os
import json
import asyncio
import aiohttp
from datetime import datetime
import asyncio
import aiohttp

class Download:

    @staticmethod
    def start():

        # =========================================
        # 설정
        # =========================================

        SYMBOL = "BTCUSD"
        INTERVAL = "5"

        TOTAL_CANDLES = 10000
        LIMIT_PER_REQUEST = 1000

        OUTPUT_FILE = os.path.join(
        os.path.dirname(__file__),
        "Raw.xlsx"
        )

        BASE_URL = "https://api.bybit.com"

        # =========================================
        # 데이터 수집
        # =========================================

        all_rows = []

        # 현재 시간(ms)
        end_time = int(time.time() * 1000)

        print("데이터 수집 시작...")

        while len(all_rows) < TOTAL_CANDLES:

            url = f"{BASE_URL}/v5/market/kline"

            params = {
                "category": "inverse",
                "symbol": SYMBOL,
                "interval": INTERVAL,
                "limit": LIMIT_PER_REQUEST,
                "end": end_time
            }

            response = requests.get(url, params=params)

            data = response.json()

            if data["retCode"] != 0:
                print("API 오류:", data)
                break

            rows = data["result"]["list"]

            if not rows:
                print("더 이상 데이터 없음")
                break

            all_rows.extend(rows)

            # 가장 오래된 timestamp
            oldest_timestamp = int(rows[-1][0])

            # 다음 요청 범위 이동
            end_time = oldest_timestamp - 1

            print(f"현재 수집 개수: {len(all_rows)}")

            time.sleep(0.2)

        # =========================================
        # 필요한 개수만 사용
        # =========================================

        all_rows = all_rows[:TOTAL_CANDLES]

        # =========================================
        # DataFrame 변환
        # =========================================

        columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "ignore_turnover"
        ]

        df = pd.DataFrame(all_rows, columns=columns)

        # turnover 제거
        df = df.drop(columns=["ignore_turnover"])

        # 시간 변환
        df["datetime"] = pd.to_datetime(
            df["timestamp"].astype("int64"),
            unit="ms"
        )

        # 정렬
        df = df.sort_values("timestamp")

        # 컬럼 순서
        df = df[
            [
                "datetime",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        ]

        # 숫자형 변환
        numeric_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        if not df.empty:
            df = df.iloc[:-1]
        # =========================================
        # 엑셀 저장
        # =========================================

        df.to_excel(OUTPUT_FILE, index=False)

        print()
        print("저장 완료")
        print(f"파일명: {OUTPUT_FILE}")
        print(f"총 캔들 수: {len(df)}")
        #parquet_file = OUTPUT_FILE.replace(".xlsx", ".parquet")
        csv_file = OUTPUT_FILE.replace(".xlsx", ".csv")
        # Parquet (추천 핵심)
        #df.to_parquet(parquet_file, index=False)

        # CSV (외부 언어용)
        df.to_csv(csv_file, index=False)


