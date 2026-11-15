# 기존 수료증 서비스 리다이렉트

`cert-redirect.yml`은 기존 Docker Compose의 공용 Traefik에서 운영·개발
수료증 주소를 `https://pseudo-lab.com/certificates`로 임시 이동시킵니다.
DNS 변경이나 수료증 애플리케이션 컨테이너, K8s 리다이렉트 리소스가 필요하지 않습니다.

`permanent: false`와 `Cache-Control: no-store`를 함께 사용합니다.
일반 GET 요청에는 302를 반환합니다. Traefik은 GET 이외의 메서드에는
메서드를 보존하는 임시 리다이렉트 307을 사용할 수 있습니다.
기존 경로와 쿼리는 목적지에 전달하지 않습니다.

## 배포

PR을 `main`에 머지한 뒤 기존 Traefik 호스트에서 최신 `main`으로 갱신하고 실행합니다.

```bash
bash scripts/ops/deploy-cert-redirect.sh
```

이 Docker 설정은 Git으로 이력을 관리하고 위 스크립트로 호스트에 배포합니다.
ArgoCD의 관리 대상은 아닙니다. 스크립트는
`/opt/traefik/dynamic/cert-redirect.yml`만 원자적으로 교체하며,
Traefik의 기존 file-provider watch가 재시작 없이 변경을 반영합니다.
공용 Traefik과 인증서 저장소는 계속 유지해야 합니다.

## 확인 및 기존 서비스 종료

HTTP/HTTPS와 `/`, `/verify`, `/api/certs/create` 경로에서 임시 리다이렉트,
정확한 Location, `Cache-Control: no-store`를 확인합니다.
기존 수료증의 GitHub Actions `certificate-system.yml`을 비활성화하여 재배포를 막고,
`cert-main` 및 `cert-dev`의 frontend/backend 컨테이너만 중단합니다.
공용 PostgreSQL과 발급 데이터는 유지합니다.

기존 상태 모니터는 리다이렉트를 따라 최종 페이지의 200 응답을 확인할 수 있습니다.

## 되돌리기

기존 수료증 컨테이너 4개를 먼저 시작한 뒤
`/opt/traefik/dynamic/cert-redirect.yml`만 제거하면 기존 Docker 라우팅으로 돌아갑니다.
필요한 경우 기존 배포 워크플로도 다시 활성화합니다.
리다이렉트 목적지 변경은 이 파일을 수정하고 동일한 PR·배포 절차를 따릅니다.
