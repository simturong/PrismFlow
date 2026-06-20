import os
import sys
import shutil
import urllib.request
import zipfile
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrismFlowBuilder")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release")
PYTHON_ZIP_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
PYTHON_ZIP_NAME = "python-3.11.9-embed-amd64.zip"

def setup_release_dirs():
    """릴리즈 빌드 폴더를 초기화 및 생성합니다."""
    if os.path.exists(RELEASE_DIR):
        logger.info(f"Clearing existing release directory: {RELEASE_DIR}")
        shutil.rmtree(RELEASE_DIR)
    os.makedirs(RELEASE_DIR, exist_ok=True)
    logger.info("Created release directory structure.")

def download_and_extract_python():
    """Embeddable Python zip 파일을 다운로드하고 압축 해제합니다."""
    embed_dir = os.path.join(RELEASE_DIR, "python-3.11.9-embed-amd64")
    os.makedirs(embed_dir, exist_ok=True)
    
    zip_path = os.path.join(RELEASE_DIR, PYTHON_ZIP_NAME)
    logger.info(f"Downloading Embeddable Python from {PYTHON_ZIP_URL}...")
    urllib.request.urlretrieve(PYTHON_ZIP_URL, zip_path)
    
    logger.info(f"Extracting {PYTHON_ZIP_NAME} to {embed_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(embed_dir)
        
    os.remove(zip_path)
    logger.info("Embeddable Python set up successfully.")
    
    # python311._pth 파일을 수정해 site-packages 및 로컬 경로를 sys.path에 추가합니다.
    pth_file = os.path.join(embed_dir, "python311._pth")
    if os.path.exists(pth_file):
        logger.info("Modifying python311._pth for relative package path matching...")
        with open(pth_file, "w") as f:
            f.write("python311.zip\n")
            f.write(".\n")
            f.write("../site-packages\n")
            f.write("../\n")
            f.write("\n")
            f.write("# Enable site packages for package loading\n")
            f.write("import site\n")

def install_dependencies():
    """requirements.txt에 정의된 의존성을 site-packages 폴더에 격리 설치합니다."""
    requirements_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    target_site_packages = os.path.join(RELEASE_DIR, "site-packages")
    os.makedirs(target_site_packages, exist_ok=True)
    
    if not os.path.exists(requirements_path):
        logger.warning("requirements.txt not found. Skipping pip install.")
        return
        
    logger.info("Installing requirements to release/site-packages target directory...")
    import subprocess
    cmd = [
        sys.executable, "-m", "pip", "install", 
        "-r", requirements_path, 
        "--target", target_site_packages
    ]
    subprocess.run(cmd, check=True)
    logger.info("Successfully installed dependencies.")

def copy_project_source():
    """PrismFlow 소스코드 및 리소스를 배포 폴더로 복사합니다."""
    logger.info("Copying project files...")
    
    # 1. main.py 복사
    shutil.copy(os.path.join(PROJECT_ROOT, "main.py"), os.path.join(RELEASE_DIR, "main.py"))
    
    # 2. prismflow 소스 패키지 복사
    src_flow = os.path.join(PROJECT_ROOT, "prismflow")
    dest_flow = os.path.join(RELEASE_DIR, "prismflow")
    
    # .venv, .pytest_cache 등 복사 제외할 필터링 정의
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in (".venv", "__pycache__", ".pytest_cache", ".git"):
                ignored.append(name)
        return ignored
        
    shutil.copytree(src_flow, dest_flow, ignore=ignore_patterns)
    logger.info("Source code and package resources copied.")

def setup_offline_pyannote_config():
    """pyannote의 오프라인 토큰리스 로드를 지원하기 위해 로컬 config.yaml 파일을 구성합니다."""
    config_dir = os.path.join(RELEASE_DIR, "prismflow", "resources", "models", "diarization")
    os.makedirs(config_dir, exist_ok=True)
    
    config_yaml_content = """pipeline:
  name: pyannote.audio.pipelines.SpeakerDiarization
  params:
    clustering: AgglomerativeClustering
    embedding: pyannote/wespeaker-voxceleb-resnet34-LM
    embedding_batch_size: 32
    embedding_exclude_overlap: true
    segmentation: pyannote/segmentation-3.0
    segmentation_batch_size: 32

params:
  clustering:
    method: centroid
    min_clusters: 1
    threshold: 0.7153814381597874
  segmentation:
    min_duration_on: 0.2679120738397295
    min_duration_off: 0.4779038472428612
"""
    yaml_path = os.path.join(config_dir, "config.yaml")
    logger.info(f"Generating offline pyannote config.yaml at: {yaml_path}")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(config_yaml_content)

def transplant_huggingface_cache():
    """사용자 PC의 huggingface 로컬 캐시에서 pyannote 모델 3종을 찾아 릴리즈 hf_cache로 복사합니다."""
    home_dir = os.path.expanduser("~")
    local_hub_dir = os.path.join(home_dir, ".cache", "huggingface", "hub")
    
    dest_hub_dir = os.path.join(RELEASE_DIR, "prismflow", "resources", "models", "hf_cache", "hub")
    
    models_to_copy = [
        "models--pyannote--segmentation-3.0",
        "models--pyannote--speaker-diarization-3.1",
        "models--pyannote--wespeaker-voxceleb-resnet34-LM"
    ]
    
    if not os.path.exists(local_hub_dir):
        logger.warning(f"Local huggingface hub cache not found at: {local_hub_dir}. Skip auto-transplant.")
        return
        
    logger.info("HF cache found. Searching gated pyannote models for offline transplant...")
    os.makedirs(dest_hub_dir, exist_ok=True)
    
    copied_count = 0
    for model in models_to_copy:
        src_path = os.path.join(local_hub_dir, model)
        dest_path = os.path.join(dest_hub_dir, model)
        if os.path.exists(src_path):
            logger.info(f"Transplanting model cache: {model} -> release/...")
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path)
            copied_count += 1
        else:
            logger.warning(f"Required model cache folder not found: {model}. End-user offline load might fail without it.")
            
    if copied_count == len(models_to_copy):
        logger.info("Successfully transplanted all 3 gated pyannote models to release bundle.")
    else:
        logger.warning(f"Transplanted {copied_count}/{len(models_to_copy)} models. Please verify models presence before shipping.")

def generate_launcher_batch():
    """배포본 원클릭 테스트 실행용 launcher.bat을 생성합니다."""
    bat_content = """@echo off
title PrismFlow - Release Runner
cd /d "%~dp0"
echo [Launcher] Launching PrismFlow using Embedded Python...
start "" "python-3.11.9-embed-amd64\\python.exe" main.py
"""
    bat_path = os.path.join(RELEASE_DIR, "launcher.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    logger.info("Created launcher.bat for quick runtime tests.")

def main():
    logger.info("========================================")
    logger.info("PrismFlow Release Builder Starting...")
    logger.info("========================================")
    
    setup_release_dirs()
    download_and_extract_python()
    install_dependencies()
    copy_project_source()
    setup_offline_pyannote_config()
    transplant_huggingface_cache()
    generate_launcher_batch()
    
    logger.info("========================================")
    logger.info("PrismFlow release bundle successfully built!")
    logger.info(f"Target location: {RELEASE_DIR}")
    logger.info("========================================")

if __name__ == "__main__":
    main()
