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


    @staticmethod
    async def realtime():
        """
        1초마다 현재가를 조회해 tick.json에 저장하면서,
        5분 마감 1초 전 타이밍마다 '하나 전 완료된 5분봉'을 조회해 업데이트합니다.
        """
        # =========================================
        # 설정
        # =========================================
        SYMBOL = "BTCUSD"
        INTERVAL = "5"
        BASE_URL = "https://api.bybit.com"

        dir_name = os.path.dirname(__file__) if '__file__' in globals() else '.'
        OUTPUT_FILE_CSV = os.path.join(dir_name, "Raw.csv")
        OUTPUT_FILE_XLSX = os.path.join(dir_name, "Raw.xlsx")
        TICK_FILE_JSON = os.path.join(dir_name, "tick.json")

        # =========================================
        # 내부 헬퍼 함수 (I/O 작업 분리)
        # =========================================
        def get_last_5min_timestamp():
            if not os.path.exists(OUTPUT_FILE_CSV):
                return 0
            try:
                df_last = pd.read_csv(OUTPUT_FILE_CSV, usecols=["timestamp"])
                return 0 if df_last.empty else int(df_last["timestamp"].iloc[-1])
            except Exception:
                return 0

        def append_5min_data(df_to_append):
            df_to_append.to_csv(OUTPUT_FILE_CSV, mode='a', header=False, index=False)
            
            if os.path.exists(OUTPUT_FILE_XLSX):
                try:
                    existing_xlsx = pd.read_excel(OUTPUT_FILE_XLSX)
                    existing_xlsx["datetime"] = pd.to_datetime(existing_xlsx["datetime"])
                    pd.concat([existing_xlsx, df_to_append], ignore_index=True).to_excel(OUTPUT_FILE_XLSX, index=False)
                except Exception: 
                    pass
            else:
                df_to_append.to_excel(OUTPUT_FILE_XLSX, index=False)

        def append_tick_json(tick_data):
            if os.path.exists(TICK_FILE_JSON):
                try:
                    with open(TICK_FILE_JSON, "r", encoding="utf-8") as f:
                        data_list = json.load(f)
                        if not isinstance(data_list, list): 
                            data_list = []
                except (json.JSONDecodeError, IOError): 
                    data_list = []
            else:
                data_list = []

            data_list.append(tick_data)
            with open(TICK_FILE_JSON, "w", encoding="utf-8") as f:
                json.dump(data_list, f, indent=4, ensure_ascii=False)

        # =========================================
        # 프로그램 시작 시 마지막 5분봉 시간 초기화
        # =========================================
        last_saved_kline_ts = await asyncio.to_thread(get_last_5min_timestamp)
        print(f"[시작] 기준 5분봉 마지막 타임스탬프: {last_saved_kline_ts}")
        print(f"[시작] 1초 현재가 수집 및 5분봉 실시간 감시를 시작합니다.\n")

        TICKER_URL = f"{BASE_URL}/v5/market/tickers"
        KLINE_URL = f"{BASE_URL}/v5/market/kline"
        
        ticker_params = {"category": "inverse", "symbol": SYMBOL}

        # =========================================
        # 1초 주기 무한 루프
        # =========================================
        async with aiohttp.ClientSession() as session:
            while True:
                start_loop_time = time.time()
                current_time_ms = int(start_loop_time * 1000)
                current_time_sec = int(start_loop_time)

                # -----------------------------------------
                # 기능 A: 1초 주기 현재가 가져오기 및 JSON 저장
                # -----------------------------------------
                try:
                    async with session.get(TICKER_URL, params=ticker_params) as ticker_resp:
                        if ticker_resp.status == 200:
                            ticker_json = await ticker_resp.json()
                            if ticker_json.get("retCode") == 0 and ticker_json["result"]["list"]:
                                ticker_info = ticker_json["result"]["list"][0]
                                current_price = ticker_info.get("lastPrice")
                                server_time_ms = ticker_json.get("time")
                                local_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                                tick_record = {
                                    "datetime": local_datetime,
                                    "timestamp": server_time_ms,
                                    "symbol": SYMBOL,
                                    "price": float(current_price)
                                }
                                await asyncio.to_thread(append_tick_json, tick_record)
                                print(f"[{local_datetime}] 현재가: {current_price}")
                except Exception as e:
                    print(f"현재가 수집 중 오류: {e}")

                # -----------------------------------------
                # 기능 B: 5분(300초) 마감 1초 전 트리거 (나머지가 299초일 때)
                # -----------------------------------------
                # 300초로 나눈 나머지가 299일 때 -> 4분 59초, 9분 59초 등 마감 1초 전 타이밍
                if current_time_sec % 300 > 1:
                    # 현재 시간보다 5분(300,000ms) 전 시점을 종점으로 잡아서 '하나 전 5분봉'을 요청
                    target_end_time = current_time_ms - 300000 
                    
                    try:
                        kline_params = {
                            "category": "inverse", "symbol": SYMBOL, "interval": INTERVAL,
                            "limit": 5, "end": target_end_time
                        }
                        async with session.get(KLINE_URL, params=kline_params) as kline_resp:
                            if kline_resp.status == 200:
                                kline_json = await kline_resp.json()
                                if kline_json.get("retCode") == 0:
                                    rows = kline_json["result"]["list"]
                                    
                                    all_rows = []
                                    for row in rows:
                                        # 중복 저장 방지: 로컬 파일의 마지막 타임스탬프보다 큰 데이터만 수집
                                        if int(row[0]) <= last_saved_kline_ts:
                                            break
                                        all_rows.append(row)

                                    if all_rows:
                                        columns = ["timestamp", "open", "high", "low", "close", "volume", "ignore_turnover"]
                                        
                                        new_df = pd.DataFrame(all_rows, columns=columns)
                                        new_df = new_df.drop(columns=["ignore_turnover"])
                                        
                                        new_df["datetime"] = pd.to_datetime(new_df["timestamp"].astype("int64"), unit="ms")
                                        new_df = new_df.sort_values("timestamp")
                                        
                                        new_df = new_df[["datetime", "timestamp", "open", "high", "low", "close", "volume"]]
                                        
                                        numeric_cols = ["open", "high", "low", "close", "volume"]
                                        for col in numeric_cols:
                                            new_df[col] = pd.to_numeric(new_df[col])

                                        await asyncio.to_thread(append_5min_data, new_df)
                                        last_saved_kline_ts = int(new_df["timestamp"].iloc[-1])
                                        print(f" ➔ [완료] 직전 마감된 5분봉 캔들 {len(new_df)}개 반영 완료. (최신 TS: {last_saved_kline_ts})")
                    except Exception as e:
                        print(f"5분봉 체크 중 오류 발생: {e}")

                    # 중복 호출 방지를 위해 트리거 직후 살짝 대기
                    await asyncio.sleep(1.1)
                    continue

                # -----------------------------------------
                # 1초 주기 정밀 조정
                # -----------------------------------------
                elapsed = time.time() - start_loop_time
                await asyncio.sleep(max(0.0, 1.0 - elapsed))