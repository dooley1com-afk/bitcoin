# App/App.py
import os
import json
import time
import threading
import webview

class ChartTheme:
    """ [디자인 설정 클래스 - 골드 네온 스타일] """
    BG_COLOR = "#080b11"              
    TEXT_COLOR = "#64748b"            
    HIGHLIGHT_COLOR = "#fbbf24"       
    LINE_COLOR = "#ffffff"            
    GRID_COLOR = "rgba(255, 255, 255, 0.015)" 
    FONT_FAMILY = "sans-serif"


class LiveChartApp:
    def __init__(self, data_dir=r"C:\Users\user\Documents\bitcoin\Data"):
        self.data_dir = data_dir
        self.csv_path = os.path.join(self.data_dir, "Raw.csv")
        self.json_path = os.path.join(self.data_dir, "tick.json")
        self.window = None

    def _get_html_template(self):
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
                <h3 class="chart-title">BTC/USD Advanced Trading Widget</h3>
                <div id="livePriceDisplay" class="live-price-text">Loading...</div>
            </div>
            <div class="canvas-wrapper"><canvas id="liveRenderChart"></canvas></div>
        </div>
        <script>
            const ctx = document.getElementById('liveRenderChart').getContext('2d');

            let lastCloseValue = 0;
            let currentLivePrice = 0;

            const chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: [],
                    datasets: [
                        {{ 
                            label: '기준선(CSV)', 
                            data: [], 
                            borderColor: '{ChartTheme.LINE_COLOR}', 
                            borderWidth: 2, 
                            fill: false,
                            tension: 0.08, 
                            pointRadius: function(context) {{
                                const count = context.dataset.data.length;
                                const csvLastIndex = count - 4; // 빈칸 3개를 뺀 실제 마지막 데이터 위치
                                return context.dataIndex === csvLastIndex ? 5 : 0;
                            }},
                            pointBackgroundColor: '{ChartTheme.LINE_COLOR}',
                            pointBorderColor: '{ChartTheme.LINE_COLOR}'
                        }},
                        {{ 
                            label: '현재가(라이브)', 
                            data: [], 
                            borderColor: '{ChartTheme.HIGHLIGHT_COLOR}', 
                            pointRadius: function(context) {{
                                return context.dataIndex === context.dataset.data.length - 1 ? 8 : 0;
                            }},
                            pointBackgroundColor: '#ffffff', 
                            pointBorderWidth: 4,
                            pointShadowColor: '{ChartTheme.HIGHLIGHT_COLOR}',
                            pointShadowBlur: 15,
                            showLine: false 
                        }}
                    ]
                }},
                options: {{
                    responsive: true, 
                    maintainAspectRatio: false,
                    animation: {{ duration: 100, easing: 'linear' }},
                    scales: {{
                        x: {{ grid: {{ color: '{ChartTheme.GRID_COLOR}' }}, ticks: {{ color: '{ChartTheme.TEXT_COLOR}', maxTicksLimit: 7, font: {{ size: 10 }} }} }},
                        y: {{ grid: {{ color: '{ChartTheme.GRID_COLOR}' }}, ticks: {{ color: '{ChartTheme.TEXT_COLOR}', font: {{ size: 11 }} }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }},
                plugins: [
                    {{
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
                    }},
                    {{
                        id: 'customTradingLines',
                        afterDatasetsDraw: (chart) => {{
                            const ctx = chart.ctx;
                            const metaCsv = chart.getDatasetMeta(0);
                            const metaLive = chart.getDatasetMeta(1);
                            
                            if (!metaCsv.data.length || !metaLive.data.length) return;

                            const totalPoints = metaCsv.data.length;
                            const csvLastIdx = totalPoints - 4; 
                            const liveLastIdx = totalPoints - 1; 

                            const csvLastPoint = metaCsv.data[csvLastIdx];
                            const liveLastPoint = metaLive.data[liveLastIdx];

                            if (!csvLastPoint || !liveLastPoint) return;

                            ctx.save();
                            
                            // [A] 수평 점선 그리기
                            ctx.beginPath();
                            ctx.lineWidth = 1.5;
                            ctx.strokeStyle = '{ChartTheme.HIGHLIGHT_COLOR}aa'; 
                            ctx.setLineDash([4, 4]); 
                            
                            ctx.moveTo(csvLastPoint.x, csvLastPoint.y);
                            ctx.lineTo(liveLastPoint.x, csvLastPoint.y); 
                            ctx.stroke();

                            // [B] 수직 실선 그리기
                            ctx.beginPath();
                            ctx.lineWidth = 1.5;
                            ctx.strokeStyle = '{ChartTheme.HIGHLIGHT_COLOR}dd';
                            ctx.setLineDash([]); // ★ 해결됨: 자바스크립트용 주석(//)으로 변경
                            
                            ctx.moveTo(liveLastPoint.x, csvLastPoint.y); 
                            ctx.lineTo(liveLastPoint.x, liveLastPoint.y); 
                            ctx.stroke();

                            ctx.restore();
                        }}
                    }}
                ]
            }});

            window.updateBaseLine = function(labels, values) {{
                const newLabels = [...labels];
                const newValues = [...values];

                if (newValues.length > 0) {{
                    lastCloseValue = newValues[newValues.length - 1];
                }}

                for(let i=1; i<=3; i++) {{
                    newLabels.push("");
                    newValues.push(null); 
                }}

                chart.data.labels = newLabels;
                chart.data.datasets[0].data = newValues;

                chart.data.datasets[1].data = new Array(newLabels.length).fill(null);
                chart.update('none');
            }};

            window.updateLiveTick = function(currentPrice) {{
                const totalCount = chart.data.datasets[0].data.length;
                if (totalCount === 0) return;

                currentLivePrice = currentPrice;
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
            title='BTC/USD Advanced Trading Widget', 
            html=html_content, 
            width=900, height=500, resizable=True
        )
        updater_thread = threading.Thread(target=self._watch_files_loop, daemon=True)
        updater_thread.start()
        webview.start()