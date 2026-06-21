import html
import re
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QFrame, QGraphicsOpacityEffect, QFileDialog
)
from PySide6.QtCore import Qt, QPropertyAnimation, QAbstractAnimation, QEasingCurve
from prismflow.agents.chat.chat_agent import ChatAgent


def markdown_to_html(md_text: str) -> str:
    """간단한 정규식 기반 Markdown to HTML 변환기.
    외부 라이브러리 없이 독립적으로 프리미엄 스타일 서식을 지원합니다.
    """
    # 1. 안전하게 HTML 이스케이프 처리
    escaped = html.escape(md_text)
    
    # 2. 코드 블록: ```python ... ```
    def replace_code_block(match):
        lang = match.group(1) or ""
        code_content = match.group(2)
        return (f'<pre style="background-color: #1a1a20; color: #cbd5e1; '
                f'padding: 8px; border-radius: 6px; font-family: Consolas, monospace; '
                f'font-size: 11px; border: 1px solid rgba(255,255,255,0.06); '
                f'margin: 6px 0; white-space: pre-wrap; word-wrap: break-word;">{code_content}</pre>')
    
    escaped = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, escaped, flags=re.DOTALL)
    
    # 3. 인라인 코드: `code`
    escaped = re.sub(
        r'`(.*?)`', 
        r'<code style="background-color: rgba(244, 63, 94, 0.15); color: #fb7185; '
        r'padding: 1px 3px; border-radius: 3px; font-family: Consolas, monospace; font-size: 11px;">\1</code>', 
        escaped
    )
    
    # 4. 제목: #, ##, ###
    escaped = re.sub(r'^### (.*?)$', r'<h3 style="color: #e2e8f0; margin-top: 8px; margin-bottom: 4px; font-size: 13px;">\1</h3>', escaped, flags=re.MULTILINE)
    escaped = re.sub(r'^## (.*?)$', r'<h2 style="color: #f1f5f9; margin-top: 10px; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 2px; font-size: 14px;">\1</h2>', escaped, flags=re.MULTILINE)
    escaped = re.sub(r'^# (.*?)$', r'<h1 style="color: #ffffff; margin-top: 12px; margin-bottom: 8px; font-size: 16px;">\1</h1>', escaped, flags=re.MULTILINE)
    
    # 5. 볼드: **text**
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #ffffff; font-weight: bold;">\1</strong>', escaped)
    
    # 6. 이탤릭: *text*
    escaped = re.sub(r'\*(.*?)\*', r'<em style="color: #94a3b8;">\1</em>', escaped)
    
    # 7. 인용구: > text
    escaped = re.sub(r'^&gt; (.*?)$', r'<blockquote style="border-left: 3px solid #7c4dff; padding-left: 6px; color: #94a3b8; margin: 6px 0; font-style: italic;">\1</blockquote>', escaped, flags=re.MULTILINE)
    
    # 8. 순서 없는 리스트: - text 또는 * text
    escaped = re.sub(r'^\s*[\-\*]\s+(.*?)$', r'<li style="color: #cbd5e1; margin-left: 8px; margin-bottom: 2px;">\1</li>', escaped, flags=re.MULTILINE)
    
    # 9. 줄바꿈 보존
    lines = []
    for line in escaped.split('\n'):
        stripped = line.strip()
        if (stripped and not stripped.startswith('<h') and not stripped.startswith('<li') 
                and not stripped.startswith('<pre') and not stripped.startswith('</pre') 
                and not stripped.startswith('<blockquote')):
            lines.append(line + '<br/>')
        else:
            lines.append(line)
            
    return '\n'.join(lines)


class ChatUI(QWidget):
    """QSS Glassmorphism 및 Markdown 출력을 지원하는 대화 패널.

    (Phase 16) 단독 오버레이 창이 아니라 PrismFlow 콘솔(FlowUI) 우측에 임베드되는 패널이다.
    창 크롬(드래그·페이드·컨트롤바·녹음표시)은 호스트 오버레이가 단독 소유한다.
    """

    def __init__(self, agent: Optional[ChatAgent] = None, parent=None):
        super().__init__(parent)
        self.agent = agent or ChatAgent()
        self.messages = []
        self._current_response_text = ""
        
        self.setWindowTitle("PrismFlow Chat Agent")
        self.resize(420, 580)
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        # 1. 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 32, 12, 12)
        layout.setSpacing(8)
        
        # 2. 상단 타이틀바 ( 제목 + 작업폴더 + 회의정보 )
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        self.title_label = QLabel("PrismFlow Chat Agent", self)
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-weight: bold;
            font-size: 13px;
            font-family: 'Segoe UI', Arial, sans-serif;
            background: transparent;
        """)

        # 작업 폴더 선택 버튼 — 웹 검색·파일 도구가 작업할 폴더(샌드박스)를 사용자가 지정.
        self.workspace_btn = QPushButton("\U0001F4C1 작업폴더", self)
        self.workspace_btn.setToolTip("웹 검색·파일 도구가 작업할 폴더를 선택합니다")
        self.workspace_btn.setCursor(Qt.PointingHandCursor)
        self.workspace_btn.setStyleSheet("""
            QPushButton {
                background: rgba(30,30,40,200); color: #e2e8f0;
                border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;
                padding: 3px 10px; font-size: 11px;
            }
            QPushButton:hover { background: rgba(124,77,255,0.35); }
        """)
        self.workspace_btn.clicked.connect(self.on_pick_workspace)

        # 회의정보 라벨 — 별도 줄을 쓰지 않고 타이틀 행 우측에 같은 줄로 배치(세로 줄 낭비 제거).
        # 한 줄에 들어가도록 컴팩트 표기(상태·발화 수·화자 수). 코디네이터가 갱신.
        self.meeting_info_label = QLabel("회의 대기 중", self)
        self.meeting_info_label.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent;"
            " font-family: 'Pretendard', 'Malgun Gothic', sans-serif;"
        )
        self.meeting_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.workspace_btn)
        title_layout.addStretch()
        title_layout.addWidget(self.meeting_info_label)
        layout.addLayout(title_layout)

        # 3. 중앙 대화 히스토리 (QTextBrowser)
        self.chat_history = QTextBrowser(self)
        self.chat_history.setOpenExternalLinks(True)
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.chat_history)
        
        # 4. 로딩 표시기 ('Claude가 생각하는 중...' 레이블)
        self.loading_label = QLabel("Claude가 답변을 작성하고 있습니다...", self)
        self.loading_label.setStyleSheet("""
            color: #a78bfa;
            font-size: 11px;
            font-style: italic;
            background: transparent;
            padding-left: 4px;
        """)
        self.loading_label.hide()
        
        # 펄스 페이드 애니메이션 적용
        self.opacity_effect = QGraphicsOpacityEffect(self.loading_label)
        self.loading_label.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1000)
        self.pulse_anim.setKeyValueAt(0.0, 0.3)
        self.pulse_anim.setKeyValueAt(0.5, 1.0)
        self.pulse_anim.setKeyValueAt(1.0, 0.3)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        
        layout.addWidget(self.loading_label)
        
        # 5. 하단 텍스트 입력창
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("세션 초기화 중... 잠시만 기다려주세요.")
        self.input_field.setEnabled(False)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(15, 15, 20, 180);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #ffffff;
                font-size: 12px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 1px solid #7c4dff;
                background-color: rgba(15, 15, 20, 220);
            }
        """)
        self.input_field.returnPressed.connect(self.send_query)
        layout.addWidget(self.input_field)
        
        # 시스템 초기화 메시지
        self.append_message("System", "AI 챗 세션을 준비하고 있습니다...")
        
    def setup_connections(self):
        self.agent.token_delivered.connect(self.on_token_delivered)
        self.agent.finished.connect(self.on_finished)
        self.agent.error_occurred.connect(self.on_error)
        self.agent.session_initialized.connect(self.on_session_initialized)
        
    def on_pick_workspace(self):
        """작업 폴더 선택 대화상자를 열어 웹/파일 도구의 작업 폴더를 지정·저장한다."""
        try:
            current = self.agent.workspace_dir()
        except Exception:
            current = ""
        path = QFileDialog.getExistingDirectory(self, "작업 폴더 선택", current)
        if path:
            self.agent.set_workspace_dir(path)
            self.append_message("System", f"작업 폴더를 설정했습니다: {path}\n(웹 검색·파일 도구가 이 폴더에서 동작합니다.)")

    def set_meeting_info(self, text: str):
        """회의정보 스트립을 갱신한다(코디네이터가 회의 시작/발화/종료 시 호출)."""
        self.meeting_info_label.setText(text)

    def on_session_initialized(self):
        self.input_field.setEnabled(True)
        self.input_field.setPlaceholderText("메시지를 입력하세요... (Enter 전송)")
        self.input_field.setFocus()
        self.append_message("System", "AI 챗 세션이 활성화되었습니다. 이제 실시간 Q&A를 진행할 수 있습니다.")

        
    def append_message(self, sender: str, text: str):
        self.messages.append({"sender": sender, "text": text})
        self.update_history_view()
        
    def update_history_view(self):
        html_content = ""
        for msg in self.messages:
            sender = msg["sender"]
            text = msg["text"]
            
            if sender == "User":
                html_content += f"""
                <div style="margin: 6px 0; text-align: right;">
                    <span style="display: inline-block; background-color: #7c4dff; color: #ffffff; 
                        padding: 8px 12px; border-radius: 12px 12px 2px 12px; max-width: 80%; 
                        text-align: left; font-family: 'Segoe UI', sans-serif; font-size: 12px; line-height: 1.4;">
                        {html.escape(text)}
                    </span>
                </div>
                """
            elif sender == "Claude":
                rendered = markdown_to_html(text)
                html_content += f"""
                <div style="margin: 6px 0; text-align: left;">
                    <div style="display: inline-block; background-color: rgba(255,255,255,0.06); 
                        border: 1px solid rgba(255,255,255,0.05); color: #cbd5e1; 
                        padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 85%; 
                        font-family: 'Segoe UI', sans-serif; font-size: 12px; line-height: 1.4;">
                        <div style="font-weight: bold; color: #a78bfa; margin-bottom: 4px; font-size: 11px;">Claude</div>
                        {rendered}
                    </div>
                </div>
                """
            else:  # System
                html_content += f"""
                <div style="margin: 8px 0; text-align: center;">
                    <span style="display: inline-block; color: #94a3b8; font-family: 'Segoe UI', sans-serif; 
                        font-size: 11px; font-style: italic; background-color: rgba(255,255,255,0.03); 
                        padding: 4px 10px; border-radius: 6px;">
                        {html.escape(text)}
                    </span>
                </div>
                """
        self.chat_history.setHtml(html_content)
        
        # 자동 스크롤
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
        
    def send_query(self):
        query = self.input_field.text().strip()
        if not query:
            return
            
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.loading_label.show()
        self.pulse_anim.start()
        
        self.append_message("User", query)
        self._current_response_text = ""
        self.agent.ask_question(query)
        
    def on_token_delivered(self, token: str):
        if not self._current_response_text:
            # 새로운 답변 시작 시
            self.messages.append({"sender": "Claude", "text": ""})
            
        self._current_response_text += token
        self.messages[-1]["text"] = self._current_response_text
        self.update_history_view()
        
    def on_finished(self, final_response: str):
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.loading_label.hide()
        self.pulse_anim.stop()
        
        if self.messages and self.messages[-1]["sender"] == "Claude":
            self.messages[-1]["text"] = final_response
        else:
            self.append_message("Claude", final_response)
        self.update_history_view()
        
    def on_error(self, err_msg: str):
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.loading_label.hide()
        self.pulse_anim.stop()
        
        self.append_message("System", f"오류가 발생했습니다: {err_msg}")
