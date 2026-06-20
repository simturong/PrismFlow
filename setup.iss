; =============================================================================
; PrismFlow Inno Setup Script
; 
; 이 스크립트는 build_release.py가 생성한 release/ 폴더 전체를
; 단일 설치 파일(PrismFlow_Setup_v1.0.exe)로 빌드합니다.
;
; 빌드 전제 조건:
;   1. Inno Setup 6 설치 (https://jrsoftware.org/isinfo.php)
;   2. build_release.py 실행 완료 → release/ 폴더 생성 완료
;
; 빌드 명령:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
;   또는
;   python build_release.py --installer
; =============================================================================

#define MyAppName "PrismFlow"
#define MyAppVersion "1.0"
#define MyAppPublisher "PrismFlow Project"
#define MyAppURL "https://github.com/prismflow"
#define MyAppExeName "launcher.bat"
#define MyAppDescription "AI 회의 어시스턴트 — 실시간 음성 전사, 회의 흐름 시각화, 맥락 기반 Q&A, 최종 회의록 자동 생성"

[Setup]
; 앱 식별
AppId={{A3F7B2C1-8D4E-4F6A-9B5C-2E1D0F3A7B8C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 설치 경로
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 출력 설정
OutputDir=dist
OutputBaseFilename=PrismFlow_Setup_v{#MyAppVersion}
SetupIconFile=

; 압축 설정 (3GB+ 페이로드에 최적화된 LZMA2 울트라 압축)
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
LZMAUseSeparateProcess=yes

; 권한 및 호환성
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; 디스크 공간 표시
DiskSpanning=no

; 언인스톨러
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\prismflow\resources\icon.ico

; 최소 Windows 버전 (Windows 10 이상)
MinVersion=10.0

; 설치 마법사 설정
WizardStyle=modern
WizardSizePercent=110,110

; 라이선스 및 정보 (선택사항 — 파일 없으면 주석 처리)
; LicenseFile=LICENSE
; InfoBeforeFile=README.md

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: checked
Name: "startupicon"; Description: "Windows 시작 시 자동 실행 등록"; GroupDescription: "시작 프로그램:"; Flags: unchecked

[Files]
; release/ 폴더 전체를 설치 대상으로 지정
; 하위 디렉토리 구조를 그대로 보존하면서 재귀 복사
Source: "release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 시작 메뉴 바로가기
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{#MyAppDescription}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"

; 바탕화면 바로가기 (선택 사항)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

; 시작 프로그램 등록 (선택 사항)
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
; 설치 완료 후 바로 실행 옵션
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} 실행"; Flags: nowait postinstall skipifsilent shellexec; WorkingDir: "{app}"

[UninstallDelete]
; 언인스톨 시 사용자 데이터는 보존하되, 앱 캐시 정리
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\core\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\agents\stt\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\agents\flow\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\agents\chat\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\agents\report\__pycache__"
Type: filesandordirs; Name: "{app}\prismflow\ui_common\__pycache__"

[Code]
// Pascal Script: 설치 전 시스템 적합성 검사
// - 마이크 장치 존재 확인
// - 하드웨어 가속 안내 (DirectX/GPU 관련)

function WaveInGetNumDevs: Integer;
external 'waveInGetNumDevs@winmm.dll stdcall';

function InitializeSetup(): Boolean;
var
  MicCount: Integer;
begin
  Result := True;
  
  // 마이크 장치 확인
  MicCount := WaveInGetNumDevs;
  if MicCount = 0 then
  begin
    if MsgBox(
      'PrismFlow는 마이크를 사용하여 실시간 음성 인식을 수행합니다.' + #13#10 +
      #13#10 +
      '현재 시스템에서 마이크 장치가 감지되지 않았습니다.' + #13#10 +
      '마이크 없이도 설치는 가능하지만, 실시간 전사 기능은 사용할 수 없습니다.' + #13#10 +
      #13#10 +
      '계속 설치하시겠습니까?',
      mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 설치 완료 후 하드웨어 가속 안내 메시지
    MsgBox(
      'PrismFlow 설치가 완료되었습니다!' + #13#10 +
      #13#10 +
      '■ 하드웨어 가속 안내:' + #13#10 +
      '  • NVIDIA GPU: CUDA 가속 (최고 속도)' + #13#10 +
      '  • Intel Arc/iGPU: OpenVINO GPU 가속' + #13#10 +
      '  • Intel NPU: OpenVINO NPU 가속' + #13#10 +
      '  • 그 외: CPU 모드 (느리지만 동작 보장)' + #13#10 +
      #13#10 +
      '설정 화면에서 하드웨어 가속 모드를 변경할 수 있습니다.' + #13#10 +
      'AUTO 모드를 권장합니다 (프로그램이 자동으로 최적의 가속을 선택합니다).',
      mbInformation, MB_OK);
  end;
end;
