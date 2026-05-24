import os
import json
import webview
import threading
from App.Chart import LiveChartApp, ChartTheme

class MainApplication:
    def __init__(self, data_dir=r"C:\Users\user\Documents\bitcoin\Data"):
        self.window = None
        self.chart_app = LiveChartApp(data_dir=data_dir)
        
        # 데이터 폴더 및 설정 파일 경로 지정
        self.data_dir = data_dir
        self.config_path = os.path.join(self.data_dir, "config.json")
        
        # 1. 저장된 설정 로드 (파일이 없으면 기본값으로 생성)
        self.settings = self._load_settings()
        
    def _load_settings(self):
        """ Data 폴더 내 config.json에서 설정을 읽어옵니다. """
        default_settings = {
            "split": 500,
            "scale": 5000
        }
        
        try:
            # 폴더가 없다면 생성
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
                
            # 파일이 있으면 읽어서 반환
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    # 저장된 값이 정상 범위인지 가볍게 검증 후 세팅
                    return {
                        "split": int(saved_data.get("split", 500)),
                        "scale": int(saved_data.get("scale", 5000))
                    }
            else:
                # 파일이 없으면 기본값으로 새로 저장
                self._save_settings(default_settings)
                return default_settings
        except Exception as e:
            print(f"[Config Load Error] 설정을 불러오지 못했습니다(기본값 대체): {e}")
            return default_settings

    def _save_settings(self, settings_dict):
        """ 현재 설정을 Data 폴더 내 config.json에 저장합니다. """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config Save Error] 설정을 저장하지 못했습니다: {e}")

    def get_ui_settings(self):
        """ 외부 모듈에서 현재 설정 값을 읽어갈 때 사용할 메서드 """
        return self.settings

    def _update_settings_from_js(self, settings_json):
        """ JS에서 변경된 값이 파이썬으로 동기화되고 파일에 자동 저장되는 콜백 """
        try:
            data = json.loads(settings_json)
            self.settings["split"] = int(data.get("split", self.settings["split"]))
            self.settings["scale"] = int(data.get("scale", self.settings["scale"]))
            
            # 슬라이더가 조작될 때마다 실시간으로 파일에 백업
            self._save_settings(self.settings)
            print(f"[Python Sync & Saved] -> Split: {self.settings['split']}, Scale: {self.settings['scale']}")
        except Exception as e:
            print(f"설정 동기화/저장 오류: {e}")

    def _get_master_html(self):
        chart_html_content = self.chart_app._get_html_template()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Crypto Trading Multi-Widget App</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            
            <style>
                html, body {{ 
                    margin: 0; padding: 0; width: 100%; height: 100%; 
                    background-color: {ChartTheme.BG_COLOR}; 
                    font-family: {ChartTheme.FONT_FAMILY}; 
                    overflow: hidden; display: flex; flex-direction: column; 
                }}
                
                /* 상단 네비게이션 바 */
                nav {{ 
                    display: flex; background: #111723; padding: 12px 25px; gap: 15px; 
                    border-bottom: 1px solid #1e293b; flex-shrink: 0; 
                }}
                nav button {{ 
                    background: #1e293b; color: {ChartTheme.TEXT_COLOR}; border: 1px solid #334155; 
                    padding: 8px 18px; border-radius: 4px; cursor: pointer; font-weight: 600; 
                    font-size: 12px; letter-spacing: 0.5px; transition: all 0.2s ease; 
                }}
                nav button:hover {{ background: #334155; color: #ffffff; }}
                nav button.active {{ 
                    background: {ChartTheme.HIGHLIGHT_COLOR}; color: #080b11; 
                    border-color: {ChartTheme.HIGHLIGHT_COLOR}; box-shadow: 0 0 10px {ChartTheme.HIGHLIGHT_COLOR}55;
                }}
                
                /* SPA 방식 컨텐츠 영역 */
                .page-content {{ flex: 1; width: 100%; position: relative; overflow: hidden; }}
                .page {{ display: none; width: 100%; height: 100%; box-sizing: border-box; }}
                .page.active {{ display: block; }}
                
                /* 차트 페이지 레이아웃 (좌: 차트, 우: 사이드 필터 패널) */
                .chart-page-container {{ display: flex; width: 100%; height: 100%; }}
                .chart-main-view {{ flex: 1; height: 100%; overflow: hidden; }}
                
                /* 우측 모던 설정 패널 */
                .chart-side-panel {{ 
                    width: 300px; height: 100%; background: #0d131f; 
                    border-left: 1px solid #1e293b; padding: 25px; box-sizing: border-box;
                    display: flex; flex-direction: column; gap: 25px; flex-shrink: 0;
                }}
                .panel-title {{ 
                    color: #ffffff; font-size: 14px; font-weight: 700; letter-spacing: 1px;
                    text-transform: uppercase; margin: 0 0 5px 0; border-bottom: 1px solid #1e293b; padding-bottom: 10px;
                }}
                
                /* 컨트롤 그룹 스타일 */
                .control-group {{ display: flex; flex-direction: column; gap: 10px; }}
                .control-label {{ color: {ChartTheme.TEXT_COLOR}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
                
                /* 슬라이더 패키지 레이아웃 (슬라이드바 + 숫자 표현) */
                .range-container {{ display: flex; align-items: center; gap: 15px; }}
                .modern-range {{
                    -webkit-appearance: none; width: 100%; height: 6px; background: #1e293b;
                    border-radius: 3px; outline: none; border: 1px solid #334155; transition: all 0.2s;
                }}
                /* 슬라이더 손잡이(Thumb) 디자인 및 인터랙션 모션 */
                .modern-range::-webkit-slider-thumb {{
                    -webkit-appearance: none; appearance: none; width: 16px; height: 16px; 
                    border-radius: 50%; background: #cbd5e1; cursor: pointer;
                    transition: transform 0.1s cubic-bezier(0.175, 0.885, 0.32, 1.275), background-color 0.2s;
                    border: 1px solid #475569;
                }}
                .modern-range::-webkit-slider-thumb:hover {{ 
                    transform: scale(1.25); 
                    background: {ChartTheme.HIGHLIGHT_COLOR}; 
                    box-shadow: 0 0 10px {ChartTheme.HIGHLIGHT_COLOR}aa;
                }}
                .modern-range::-webkit-slider-thumb:active {{ 
                    transform: scale(1.4); 
                }}
                
                /* 실시간 수치 표시 텍스트 디자인 (sans-serif 유지) */
                .range-value {{ 
                    color: #ffffff; font-size: 13px; font-weight: bold; 
                    min-width: 45px; text-align: right; font-family: {ChartTheme.FONT_FAMILY};
                }}

                /* 기존 차트 크기 레이아웃 보존 */
                .widget-container {{ padding: 25px; box-sizing: border-box; width: 100%; height: 100%; }}
                .info-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
                .chart-title {{ margin: 0; font-size: 13px; color: {ChartTheme.TEXT_COLOR}; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; }}
                .live-price-text {{ font-size: 26px; font-weight: bold; color: {ChartTheme.HIGHLIGHT_COLOR}; text-shadow: 0 0 12px {ChartTheme.HIGHLIGHT_COLOR}cc; }}
                .canvas-wrapper {{ position: relative; width: 100%; height: calc(100% - 60px); }}
                
                /* 서브 페이지 기본 스타일 */
                .sub-page-wrapper {{ padding: 40px; color: #cbd5e1; }}
                .sub-page-title {{ color: #ffffff; font-size: 22px; margin-bottom: 15px; border-left: 4px solid {ChartTheme.HIGHLIGHT_COLOR}; padding-left: 12px; }}
            </style>
        </head>
        <body>

            <nav id="navBar">
                <button onclick="switchPage('chart', this)" class="active">LIVE CHART</button>
                <button onclick="switchPage('trading', this)">TRADING</button>
                <button onclick="switchPage('settings', this)">SETTINGS</button>
            </nav>

            <div class="page-content">
                <div id="page-chart" class="page active">
                    <div class="chart-page-container">
                        <div class="chart-main-view">
                            {self._extract_chart_body(chart_html_content)}
                        </div>
                        
                        <div class="chart-side-panel">
                            <h3 class="panel-title">Chart Options</h3>
                            
                            <div class="control-group">
                                <span class="control-label">SPLIT DISPLAY (50 STEP)</span>
                                <div class="range-container">
                                    <input type="range" id="splitSlider" class="modern-range" min="100" max="1000" step="50" value="{self.settings['split']}" oninput="updateDisplayValue('splitValText', this.value)" onchange="syncSettingsToPython()">
                                    <span id="splitValText" class="range-value">{self.settings['split']}</span>
                                </div>
                            </div>
                            
                            <div class="control-group">
                                <span class="control-label">CHART SCALE (500 STEP)</span>
                                <div class="range-container">
                                    <input type="range" id="scaleSlider" class="modern-range" min="1000" max="10000" step="500" value="{self.settings['scale']}" oninput="updateDisplayValue('scaleValText', this.value)" onchange="syncSettingsToPython()">
                                    <span id="scaleValText" class="range-value">{self.settings['scale']}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="page-trading" class="page">
                    <div class="sub-page-wrapper">
                        <h2 class="sub-page-title">Trading Panel</h2>
                        <p>주문 생성 영역</p>
                    </div>
                </div>

                <div id="page-settings" class="page">
                    <div class="sub-page-wrapper">
                        <h2 class="sub-page-title">Configuration</h2>
                        <p>설정 영역</p>
                    </div>
                </div>
            </div>

            <script>
                function switchPage(pageId, btn) {{
                    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
                    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
                    document.getElementById('page-' + pageId).classList.add('active');
                    btn.classList.add('active');
                }}

                function updateDisplayValue(targetId, val) {{
                    document.getElementById(targetId).innerText = val;
                }}

                function syncSettingsToPython() {{
                    const splitVal = document.getElementById('splitSlider').value;
                    const scaleVal = document.getElementById('scaleSlider').value;
                    
                    const settings = {{
                        split: parseInt(splitVal),
                        scale: parseInt(scaleVal)
                    }};
                    
                    pywebview.api.update_settings(JSON.stringify(settings));
                }}
            </script>
            
            {self._extract_chart_script(chart_html_content)}
            
        </body>
        </html>
        """

    def _extract_chart_body(self, html):
        start = html.find('<div class="widget-container">')
        end = html.find('<script>')
        return html[start:end].strip()

    def _extract_chart_script(self, html):
        start = html.find('<script>')
        end = html.rfind('</script>') + 9
        return html[start:end]

    def run(self):
        master_html = self._get_master_html()
        
        class BridgeAPI:
            def __init__(self, app_instance):
                self.app = app_instance
            def update_settings(self, settings_json):
                self.app._update_settings_from_js(settings_json)
        
        self.window = webview.create_window(
            title='Crypto Trading Dashboard',
            html=master_html,
            width=1250, 
            height=680,
            resizable=True,
            js_api=BridgeAPI(self) 
        )
        
        self.chart_app.window = self.window
        
        updater_thread = threading.Thread(target=self.chart_app._watch_files_loop, daemon=True)
        updater_thread.start()
        
        webview.start()