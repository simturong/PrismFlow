import os
from pathlib import Path

def get_mermaid_html() -> str:
    """오프라인용 로컬 번들 Mermaid.js 및 svg-pan-zoom.min.js를 임베드한 반투명 다크 Glassmorphism 스타일 HTML을 반환합니다.
    
    f-string 파싱 오류를 원천 차단하기 위해 일반 문자열과 플레이스홀더 치환 방식을 사용하며,
    부드러운 실시간 줌/팬 제어, 다크 Glassmorphic 줌 툴바 UI, 다이어그램 갱신 시 상태 보존 로직을 내장합니다.
    """
    current_dir = Path(__file__).parent.absolute()
    mermaid_js_path = current_dir / "resources" / "mermaid.min.js"
    panzoom_js_path = current_dir / "resources" / "svg-pan-zoom.min.js"
    
    # Windows 백슬래시 경로를 file:/// URL 스키마로 변환
    mermaid_js_url = mermaid_js_path.as_uri()
    panzoom_js_url = panzoom_js_path.as_uri()
    
    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PrismFlow Flow Visualization</title>
    <style>
        body {
            background-color: transparent;
            margin: 0;
            padding: 2px;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            color: #e0e0e0;
            height: 100vh;
            box-sizing: border-box;
            overflow: hidden;
        }
        #diagram-container {
            width: 100%;
            height: 100%;
            background: rgba(30, 30, 35, 0.7);
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            transition: all 0.3s ease-in-out;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            overflow: hidden;
            box-sizing: border-box;
            position: relative;
        }
        /* 다이어그램 교체 시 부드러운 페이드/슬라이드 인 (다이나믹 전환) */
        .mermaid {
            opacity: 0;
            transform: translateY(8px) scale(0.98);
            transition: opacity 0.45s ease-out, transform 0.45s ease-out;
            width: 100%;
            height: 100%;
        }
        .mermaid.fade-in {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
        /* svg-pan-zoom 라이브러리가 크기 조정을 자체 주도하도록 기존 강제 max-width 제거 */
        #diagram-container svg {
            width: 100% !important;
            height: 100% !important;
            max-width: none !important;
            max-height: none !important;
        }
        /* 노드 라벨 줄바꿈 허용(긴 한국어가 박스를 넘쳐 잘리지 않게) */
        .mermaid .nodeLabel, .mermaid .label, .mermaid span.nodeLabel {
            white-space: normal !important;
            word-break: keep-all;
            line-height: 1.25;
        }
        
        /* 다크 Glassmorphism 줌 컨트롤 툴바 */
        #zoom-controls {
            position: absolute;
            bottom: 16px;
            right: 16px;
            z-index: 1000;
            background: rgba(30, 30, 35, 0.65);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 4px;
            display: flex;
            gap: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            user-select: none;
        }
        .zoom-btn {
            background: transparent;
            border: none;
            color: #e2e8f0;
            font-size: 13px;
            width: 28px;
            height: 28px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.2s, color 0.2s;
        }
        .zoom-btn:hover {
            background-color: rgba(255, 255, 255, 0.08);
            color: #5eead4; /* 청록색 강조 */
        }
        .zoom-btn:active {
            background-color: rgba(255, 255, 255, 0.15);
        }
    </style>
    <script src="__MERMAID_JS_URL__"></script>
    <script src="__SVG_PAN_ZOOM_JS_URL__"></script>
    <script>
        // Mermaid 초기화
        mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            themeVariables: {
                background: 'transparent',
                primaryColor: '#1e1e24',
                primaryTextColor: '#ffffff',
                lineColor: '#03a9f4',
                secondaryColor: '#2d2d35',
                tertiaryColor: '#1a1a20',
                fontSize: '20px'
            },
            flowchart: { useMaxWidth: false, htmlLabels: true, padding: 14, nodeSpacing: 45, rankSpacing: 45, wrappingWidth: 220 },
            securityLevel: 'loose'
        });
        
        var panZoomInstance = null;
        var lastZoom = null;
        var lastPan = null;
        
        // 동적 렌더링 및 줌/팬 복원 기능
        function updateDiagram(mermaidCode) {
            const container = document.getElementById('diagram-container');
            
            // 1. 기존 인스턴스 줌/팬 좌표 백업 및 해제
            if (panZoomInstance) {
                try {
                    lastZoom = panZoomInstance.getZoom();
                    lastPan = panZoomInstance.getPan();
                    panZoomInstance.destroy();
                } catch (e) {
                    console.warn("Failed to destroy pan-zoom instance:", e);
                }
                panZoomInstance = null;
            }
            
            // 디코딩 처리 (Base64 디코딩으로 이스케이프 문자 등 깨짐 방지)
            const decodedCode = decodeURIComponent(escape(window.atob(mermaidCode)));
            
            // 고유 ID 생성을 위해 현재 타임스탬프 결합
            const uniqueId = 'mermaid-svg-' + Date.now();
            
            container.innerHTML = '<div class="mermaid" id="' + uniqueId + '">' + decodedCode + '</div>';

            try {
                // Mermaid v10+ 호환 동적 렌더링 실행
                mermaid.run({
                    nodes: [document.getElementById(uniqueId)]
                });
                
                // 렌더 직후 fade-in 클래스 부여 및 줌/팬 바인딩
                requestAnimationFrame(function() {
                    var el = document.getElementById(uniqueId);
                    if (el) { 
                        el.classList.add('fade-in'); 
                        
                        // 2. 렌더 완료 후 생성된 SVG 요소를 가져와 svg-pan-zoom 초기화
                        const svgEl = el.querySelector('svg');
                        if (svgEl) {
                            svgEl.style.width = '100%';
                            svgEl.style.height = '100%';
                            
                            panZoomInstance = svgPanZoom(svgEl, {
                                zoomEnabled: true,
                                controlIconsEnabled: false, // 커스텀 UI 사용
                                fit: true,
                                center: true,
                                minZoom: 0.1,
                                maxZoom: 10,
                                zoomScaleSensitivity: 0.2
                            });
                            
                            // 3. 백업된 이전 상태 복원 (처음 로드가 아닐 때만)
                            if (lastZoom !== null && lastPan !== null) {
                                try {
                                    panZoomInstance.zoom(lastZoom);
                                    panZoomInstance.pan(lastPan);
                                } catch (err) {
                                    console.warn("Failed to restore zoom/pan:", err);
                                }
                            }
                        }
                    }
                });
            } catch (e) {
                console.error("Mermaid Dynamic Render Exception: ", e);
                container.innerHTML = '<div style="color: #ff5252; padding: 20px; font-weight: bold;">다이어그램 렌더링 에러:<br/>' + e.message + '</div>';
            }
        }
        
        // 돋보기 컨트롤 바 바인딩
        window.addEventListener('DOMContentLoaded', function() {
            document.getElementById('btn-zoom-in').addEventListener('click', function(e) {
                e.preventDefault();
                if (panZoomInstance) panZoomInstance.zoomIn();
            });
            document.getElementById('btn-zoom-out').addEventListener('click', function(e) {
                e.preventDefault();
                if (panZoomInstance) panZoomInstance.zoomOut();
            });
            document.getElementById('btn-zoom-fit').addEventListener('click', function(e) {
                e.preventDefault();
                if (panZoomInstance) {
                    panZoomInstance.fit();
                    panZoomInstance.center();
                }
            });
            document.getElementById('btn-zoom-reset').addEventListener('click', function(e) {
                e.preventDefault();
                if (panZoomInstance) {
                    panZoomInstance.reset();
                    panZoomInstance.fit();
                    panZoomInstance.center();
                }
            });
        });
    </script>
</head>
<body>
    <div id="diagram-container">
        <div style="text-align: center; color: #a0a0a0; font-size: 14px; letter-spacing: 1px;">
            <p>회의 발화 데이터를 수집하고 있습니다...</p>
            <p style="font-size: 11px; color: #707070;">대화가 쌓이면 흐름도가 실시간으로 갱신됩니다.</p>
        </div>
    </div>
    
    <!-- 돋보기 컨트롤 패널 -->
    <div id="zoom-controls">
        <button class="zoom-btn" id="btn-zoom-in" title="확대">➕</button>
        <button class="zoom-btn" id="btn-zoom-out" title="축소">➖</button>
        <button class="zoom-btn" id="btn-zoom-fit" title="화면맞춤">🎯</button>
        <button class="zoom-btn" id="btn-zoom-reset" title="1:1 리셋">🔄</button>
    </div>
</body>
</html>
"""
    return html_template.replace("__MERMAID_JS_URL__", mermaid_js_url).replace("__SVG_PAN_ZOOM_JS_URL__", panzoom_js_url)
