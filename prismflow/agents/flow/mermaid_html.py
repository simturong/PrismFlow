import os
from pathlib import Path

def get_mermaid_html() -> str:
    """오프라인용 로컬 번들 Mermaid.js를 임베드한 반투명 다크 Glassmorphism 스타일 HTML을 반환합니다.
    
    f-string 파싱 오류를 원천 차단하기 위해 일반 문자열과 플레이스홀더 치환 방식을 사용하며,
    새로고침 없이 JS DOM 제어로 다이어그램을 업데이트할 수 있는 updateDiagram() 자바스크립트 인터페이스를 내장합니다.
    """
    current_dir = Path(__file__).parent.absolute()
    js_path = current_dir / "resources" / "mermaid.min.js"
    # Windows 백슬래시 경로를 file:/// URL 스키마로 변환
    js_url = js_path.as_uri()
    
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
            /* 좌우 여백을 줄이고 세로로 긴 그래프는 축소(가독성↓) 대신 스크롤 */
            display: flex;
            justify-content: center;
            align-items: flex-start;
            overflow: auto;
            box-sizing: border-box;
        }
        /* 다이어그램 교체 시 부드러운 페이드/슬라이드 인 (다이나믹 전환) */
        .mermaid {
            opacity: 0;
            transform: translateY(8px) scale(0.98);
            transition: opacity 0.45s ease-out, transform 0.45s ease-out;
            width: 100%;
        }
        .mermaid.fade-in {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
        /* svg는 폭을 꽉 채우되(좌우 여백 최소화), 세로는 자연 크기로 두고 컨테이너가 스크롤 */
        #diagram-container svg {
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
            max-height: none !important;
        }
        /* 노드 라벨 줄바꿈 허용(긴 한국어가 박스를 넘쳐 잘리지 않게) */
        .mermaid .nodeLabel, .mermaid .label, .mermaid span.nodeLabel {
            white-space: normal !important;
            word-break: keep-all;
            line-height: 1.25;
        }
    </style>
    <script src="__MERMAID_JS_URL__"></script>
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
            flowchart: { useMaxWidth: true, htmlLabels: true, padding: 14, nodeSpacing: 45, rankSpacing: 45, wrappingWidth: 220 },
            securityLevel: 'loose'
        });
        
        // 동적 렌더링용 자바스크립트 인터페이스
        function updateDiagram(mermaidCode) {
            const container = document.getElementById('diagram-container');
            
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
                // 렌더 직후 fade-in 클래스 부여 → 부드러운 전환 애니메이션 트리거
                requestAnimationFrame(function() {
                    var el = document.getElementById(uniqueId);
                    if (el) { el.classList.add('fade-in'); }
                });
            } catch (e) {
                console.error("Mermaid Dynamic Render Exception: ", e);
                container.innerHTML = '<div style="color: #ff5252; padding: 20px; font-weight: bold;">다이어그램 렌더링 에러:<br/>' + e.message + '</div>';
            }
        }
    </script>
</head>
<body>
    <div id="diagram-container">
        <div style="text-align: center; color: #a0a0a0; font-size: 14px; letter-spacing: 1px;">
            <p>회의 발화 데이터를 수집하고 있습니다...</p>
            <p style="font-size: 11px; color: #707070;">대화가 쌓이면 흐름도가 실시간으로 갱신됩니다.</p>
        </div>
    </div>
</body>
</html>
"""
    return html_template.replace("__MERMAID_JS_URL__", js_url)
