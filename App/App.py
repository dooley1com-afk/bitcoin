# App/App.py
import os
import json
import time
import threading
import webview

class ChartTheme:
    """ 
    [★ 디자인 설정 클래스 - 골드 네온 스타일 수정] 
    """
    BG_COLOR = "#080b11"              # 더 깊고 어두운 밤하늘 배경색 (다크 네이비 블랙)
    TEXT_COLOR = "#64748b"            # 그리드 문자 색상 (차분한 슬레이트 그레이)
    HIGHLIGHT_COLOR = "#fbbf24"       # 실시간 가격 강조 색상 (★ 찬란한 메탈릭 골드)
    LINE_COLOR = "#ffffff"            # ★ 차트 기준선 색상 (깔끔한 퓨어 화이트)
    GRID_COLOR = "rgba(255, 255, 255, 0.015)" # 배경 격자 무늬 투명도 조절
    FONT_FAMILY = "sans-serif"


class LiveChartApp:
    """
    [앱 구동 클래스]
    내부 기능적 로직은 기존과 100% 동일하며, 오직 렌더링 스타일 속성만 변환되었습니다.
    """
    def __init__(self, data_dir=r"C:\Users\user\Documents\bitcoin\Data"):
        self.data_dir = data_dir
        self.csv_path = os.path.join(self.data_dir, "Raw.csv")
        self.json_path = os.path.join(self.data_dir, "tick.json")
        self.window = None

    def _get_html_template(self):
        """ChartTheme의 금색 디자인 설정을 주입받아 완성된 HTML을 반환합니다."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: {ChartTheme.BG_COLOR}; font-family: {ChartTheme.FONT_FAMILY}; overflow: hidden; }}
                .widget-container {{ padding: 25px; box-sizing: border-box; width: 100%; height: 100%; }}
                .info-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
                .chart-title {{ margin: 0; font-size: 13px; color: {ChartTheme.TEXT_COLOR}; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; }}
                .live-price-text {{ font-size: 26px; font-weight: bold; color: {ChartTheme.HIGHLIGHT_COLOR}; text-shadow: 0 0 12px {ChartTheme.HIGHLIGHT_COLOR}cc; }}
                .canvas-wrapper {{ position: relative; width: 100%; height: calc(100% - 50px); }}
            </style>
        </head>
        <body>
        <div class="widget-container">
            <div class="info-header">
                <h3 class="chart-title">BTC/USD Pure White & Gold Live Monitor</h3>
                <div id="livePriceDisplay" class="live-price-text">- USD</div>
            </div>
            <div class="canvas-wrapper"><canvas id="liveRenderChart"></canvas></div>
        </div>
        <script>
            const ctx = document.getElementById('liveRenderChart').getContext('2d');

            const chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: [],
                    datasets: [
                        {{ 
                            label: '기준선', 
                            data: [], 
                            borderColor: '{ChartTheme.LINE_COLOR}', 
                            borderWidth: 2, 
                            fill: false,                 // ★ 차트 밑에 차 있는 색상 제거 (투명하게)
                            tension: 0.08, 
                            pointRadius: 0 
                        }},
                        {{ 
                            label: '현재가', 
                            data: [], 
                            borderColor: '{ChartTheme.HIGHLIGHT_COLOR}', 
                            pointRadius: 8,              // 점 크기 확대
                            pointBackgroundColor: '#ffffff', // 중앙부는 백색으로 빛나게
                            pointBorderWidth: 4,         // 금빛 테두리 두께 강화
                            
                            // ★ 중요: 웅웅거리며 번지는 금빛 네온 효과 연출 (그림자 속성 부여)
                            pointShadowColor: '{ChartTheme.HIGHLIGHT_COLOR}',
                            pointShadowBlur: 15,
                            showLine: false 
                        }}
                    ]
                }},
                options: {{
                    responsive: true, 
                    maintainAspectRatio: false,
                    animation: {{ duration: 120, easing: 'linear' }},
                    scales: {{
                        x: {{ grid: {{ color: '{ChartTheme.GRID_COLOR}' }}, ticks: {{ color: '{ChartTheme.TEXT_COLOR}', maxTicksLimit: 7, font: {{ size: 10 }} }} }},
                        y: {{ grid: {{ color: '{ChartTheme.GRID_COLOR}' }}, ticks: {{ color: '{ChartTheme.TEXT_COLOR}', font: {{ size: 11 }} }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }},
                // Chart.js에서 점에 그림자 광원 효과(웅웅거리는 느낌)를 주기 위한 커스텀 플러그인 탑재
                plugins: [{{
                    id: 'pointShadow',
                    beforeDraw: (chart) => {{
                        const ctx = chart.ctx;
                        ctx.save();
                        const dataset = chart.data.datasets[1];
                        if (dataset && dataset.pointShadowBlur) {{
                            ctx.shadowColor = dataset.pointShadowColor;
                            ctx.shadowBlur = dataset.pointShadowBlur;
                        }}
                    }},
                    afterDraw: (chart) => {{
                        chart.ctx.restore();
                    }}
                }}]
            }});

            window.updateBaseLine = function(labels, values) {{
                chart.data.labels = labels;
                chart.data.datasets[0].data = values;
                if (chart.data.datasets[1].data.length !== labels.length) {{
                    chart.data.datasets[1].data = new Array(labels.length).fill(null);
                }}
                chart.update('none');
            }};

            window.updateLiveTick = function(currentPrice) {{
                const totalCount = chart.data.datasets[0].data.length;
                if (totalCount === 0) return;
                document.getElementById('livePriceDisplay').innerText = '$' + currentPrice.toLocaleString(undefined, {{minimumFractionDigits: 1}});
                const tickDataArray = new Array(totalCount).fill(null);
                tickDataArray[totalCount - 1] = currentPrice;
                chart.data.datasets[1].data = tickDataArray;
                chart.update();
            }};
        </script>
        </body>
        </html>
        """

    def _watch_files_loop(self):
        """데이터를 파싱하고 전달하는 이 로직 기능은 이전과 완벽히 동일하여 충돌이 일어나지 않습니다."""
        time.sleep(1.5)
        last_csv_size, last_json_size = 0, 0
        
        while True:
            if not self.window:
                break
            try:
                if os.path.exists(self.csv_path):
                    csv_size = os.path.getsize(self.csv_path)
                    if csv_size != last_csv_size and csv_size > 0:
                        with open(self.csv_path, 'r', encoding='utf-8') as f:
                            lines = f.read().strip().split('\n')
                        if len(lines) >= 2:
                            headers = lines[0].split(',')
                            dt_idx, close_idx = headers.index('datetime'), headers.index('close')
                            target_rows = lines[-100:]
                            labels, values = [], []
                            for row_str in target_rows:
                                row = row_str.split(',')
                                if len(row) > max(dt_idx, close_idx):
                                    labels.append(row[dt_idx][11:16])
                                    values.append(float(row[close_idx]))
                            
                            last_csv_size = csv_size
                            self.window.evaluate_js(f"window.updateBaseLine({json.dumps(labels)}, {json.dumps(values)});")

                if os.path.exists(self.json_path):
                    json_size = os.path.getsize(self.json_path)
                    if json_size != last_json_size and json_size > 0:
                        with open(self.json_path, 'r', encoding='utf-8') as f:
                            tick_data = json.load(f)
                        if isinstance(tick_data, list) and len(tick_data) > 0:
                            live_price = float(tick_data[-1].get('price', 0))
                            last_json_size = json_size
                            self.window.evaluate_js(f"window.updateLiveTick({live_price});")
                            
            except (json.JSONDecodeError, PermissionError):
                pass 
            except Exception:
                pass
                
            time.sleep(0.5)

    def run(self):
        html_content = self._get_html_template()
        self.window = webview.create_window(
            title='BTC/USD 화이트 골드 모니터 위젯', 
            html=html_content, 
            width=900, height=500, resizable=True
        )
        updater_thread = threading.Thread(target=self._watch_files_loop, daemon=True)
        updater_thread.start()
        webview.start()