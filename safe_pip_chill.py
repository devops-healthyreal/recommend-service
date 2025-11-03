import os
import importlib.metadata

def safe_pip_chill():
    """
    pip-chill 대체 스크립트
    - METADATA 누락된 패키지를 건너뛰고
    - 정상 패키지의 이름과 버전을 출력
    """
    packages = []
    errors = []

    for dist in importlib.metadata.distributions():
        try:
            name = dist.metadata["Name"]
            version = dist.version
            packages.append(f"{name}=={version}")
        except (KeyError, FileNotFoundError):
            # METADATA 파일이 없거나 깨진 경우
            errors.append(dist.locate_file(''))
            continue

    print("정상적으로 인식된 패키지 목록:\n")
    for pkg in sorted(packages, key=lambda x: x.lower()):
        print(pkg)

    if errors:
        print("\n다음 패키지의 METADATA 파일이 누락되어 건너뛰었습니다:\n")
        for e in errors:
            print(f" - {e}")

if __name__ == "__main__":
    safe_pip_chill()
