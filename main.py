# main.py
from Data.Download import Download
from Window import MainApplication  # 객체화된 클래스를 임포트
import asyncio
import threading

def run_async_download():
    """데이터 수집 엔진을 백그라운드에서 구동"""
    try:
        asyncio.run(Download.realtime())
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[시스템] 데이터 다운로드 엔진이 안전하게 종료되었습니다.")
    except Exception as e:
        print(f"[시스템 오류] 실시간 다운로드 중 오류 발생: {e}")


def main():
    # 1. 초기 데이터 수집 스타트
    Download.start()
    
    # 2. 비동기 다운로드 로직을 별도의 스레드(백그라운드)로 분리
    download_thread = threading.Thread(target=run_async_download, daemon=True)
    download_thread.start()
    print("[시스템] 백그라운드 실시간 수집 엔진이 가동되었습니다.")
    
    # 3. [핵심] 차트 앱 객체 생성 및 실행 (메인 스레드에서 구동)
    try:
        print("[시스템] 라이브 차트 뷰어를 시작합니다...")
        app = MainApplication()
        app.run()
    except Exception as e:
        print(f"[UI 오류] 뷰어 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()