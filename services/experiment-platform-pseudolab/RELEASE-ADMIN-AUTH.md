# 관리자 인증 릴리스 절차

이 변경은 운영 반영 전 준비다. 이 PR 또는 앱 PR을 병합하는 순간 자동 배포가 시작되므로, 운영 실행 승인 전에는 병합하거나 workflow_dispatch·Argo sync·kubectl apply를 실행하지 않는다.

## 준비한 변경과 근거

- 앱 후보: [experiment-platform-pseudolab PR #25](https://github.com/Pseudo-Lab/experiment-platform-pseudolab/pull/25), 검증한 head `3d04abe37fff2c30e520cbbb8f59c1bc41cdea41`.
- 2026-10-27 기준 앱 main 및 운영 이미지: `ca7d7a09a0bf99dae1d9e5bdf922ad921d105111`. Ops 준비 기준 main: `1ea42373294fad3a034f98fc9cbc15ab3a53cf8b`.
- 기존 로그인 PR #12는 보존한다. PR #25는 기존 로그인 구현에 세션·API 보호 보완을 포함한다. 로그인 작업의 별도 정리를 기다릴 필요는 없다.
- 기존 Cloudflare/D1/R2 암호문 7개는 변경하지 않았다. 새 관리자 계정·비밀번호 해시·세션 서명키 및 쿠키/CORS 설정 6개만 strict scope로 암호화했다.
- `AUTH_COOKIE_SECURE=true`, `AUTH_COOKIE_SAMESITE=lax`. `BACKEND_CORS_ORIGINS`에는 기존 SDK용 `*`와 정확한 관리자 origin `https://exp.pseudolab-devfactory.com`을 함께 둔다. 앱의 관리자 Origin 검사는 `*`를 신뢰 목록에서 제외한다. ingress 뒤의 내부 HTTP 주소와 관계없이 HTTPS 관리 origin을 허용하기 위해 정확한 origin이 필요하다.
- 초기 관리자 로그인 정보는 Git·PR·댓글·공용 로그에 넣지 않는다. 준비 담당자의 접근 제한 파일로 별도 전달한다. 현재 운영에는 활성화되지 않았다.
- 운영 컨트롤러의 공개 인증서로 암호화했고, 컨트롤러의 읽기 전용 `/v1/verify` 검증, 전체 overlay render, API 서버 dry-run을 통과했다. 검증 전후 Secret·SealedSecret·두 Deployment의 resourceVersion은 동일했다. 이미지 태그도 변경하지 않았다.

## 운영 실행 승인을 받은 뒤의 순서

1. 변경된 main/PR head, 해당 날짜의 원격 반영 제한, 현재 Argo 상태를 다시 확인한다. 관련 앱 main에 동시 병합이 없도록 조율한다. 승인 대상 head에서 바뀌었으면 변경 부분을 재검토한다.
2. 이 Ops PR의 CI 성공을 확인한 뒤 먼저 병합한다. Argo 자동 동기화와 SealedSecret `Synced=True`를 기다린다. 기존 이미지의 재시작이 발생할 수 있으므로 backend rollout도 확인한다.

   ```sh
   kubectl -n argocd get application experiment-platform -o jsonpath='{.status.sync.status} {.status.health.status} {.status.sync.revision}{"\n"}'
   kubectl -n experiment-platform get sealedsecret experiment-platform-backend-secret -o jsonpath='{.status.conditions}{"\n"}'
   kubectl -n experiment-platform get secret experiment-platform-backend-secret -o go-template='{{range $key, $value := .data}}{{printf "%s\n" $key}}{{end}}'
   kubectl -n experiment-platform rollout status deployment/experiment-platform-backend --timeout=180s
   ```

   새 설정 6개가 Secret의 **키 이름**으로 모두 존재해야 한다. 값은 터미널에 출력하지 않는다. 여기까지 앱 이미지는 기존 SHA이며 구버전 관리 API는 아직 인증으로 보호되지 않는다. 암호화 검증은 값의 적용·Pod 기동·HTTPS 로그인 성공을 대신하지 않는다.

3. 설정 반영이 성공한 후 앱 PR #25의 최신 CI와 head를 확인하고 병합한다. 앱 `ci` 성공 → `gitops-ci`의 ARM64 이미지 게시 → Ops main의 두 이미지 태그 자동 갱신 → Argo 자동 동기화 순서로 운영에 반영된다. 수동 workflow_dispatch는 중복 실행하지 않는다.
4. 앱 main 병합 SHA, 성공한 CI의 head SHA, gitops-ci checkout/이미지 SHA, Ops 두 이미지 태그와 실제 Pod imageID를 대조한다. workflow는 main checkout 및 `github.sha`를 사용하므로 동시 main 변경 시 검증한 SHA와 달라질 수 있다. 불일치하면 완료로 보고하지 않는다.
5. 두 Deployment의 rollout과 Argo Synced/Healthy를 확인하고 아래 운영 검증을 수행한다. 단순 Ready는 HTTP 기능 검증이 아니다.

## 운영 반영 후 확인

- HTTPS `/login` 및 기존 관리 경로가 로드되고 미로그인 사용자는 로그인으로 이동한다. 미로그인 관리 API는 401, 인증 설정이 누락된 경우 503으로 차단돼야 한다.
- 초기 관리자 정보로 로그인하고 HTTPS 전용·HttpOnly·SameSite=lax 쿠키, 페이지 새로고침 후 세션 복원, 관리 화면의 읽기 동작, 로그아웃 후 401을 확인한다. 비밀번호·쿠키를 스크린샷이나 로그에 남기지 않는다.
- 관리 요청의 외부 Origin은 403이어야 한다. 기존 외부 SDK의 preflight와 API-key/Bearer 호출은 기존 계약을 유지해야 한다. 실제 소비자 서비스에서 읽기 중심 확인을 우선하고, 데이터 생성·키 발급·회전은 별도 승인 없이 하지 않는다.
- 인증과 무관한 D1/R2 연결·실제 소비자 SDK는 운영 전 로컬 smoke로 완전히 검증할 수 없다. 운영 오류와 접근 로그를 확인하고 실패가 있으면 아래 중단 기준을 따른다.

## 중단 및 복구 기준

- Ops 설정 반영 또는 기존 이미지 재시작이 실패하면 앱 병합을 중단한다. 준비한 암호문과 live 이름/namespace, SealedSecret 조건, Pod 이벤트를 확인한다. 기존 Cloudflare/D1/R2 값은 교체하지 않는다.
- CI·이미지 게시·Ops 자동 태그 변경 중 어느 단계든 실패하면 후속 단계를 수동으로 건너뛰지 않는다. 마지막 성공 SHA와 실제 운영 상태를 확인하고 실패 원인을 수정한다.
- 새 앱에서 인증 누락, 비인증 관리 API 허용, 신뢰하지 않는 Origin 허용, 로그인 불가 또는 SDK 장애가 확인되면 완료로 선언하지 않는다. 가능한 경우 보안 backend를 유지하고 문제 부분만 고친다.
- 기존 `ca7d7a0` backend로 단순 롤백하면 미인증 관리 API 노출이 복구되므로 안전한 기본 복구가 아니다. 보안 backend를 유지할 수 없다면 운영자와 서비스 중단을 결정하고 Ops에서 backend replicas를 0으로 내려 접근을 먼저 중단한 뒤 수정한다. 이 경우 SDK/API도 중단되는 영향을 함께 알린다. 자동 selfHeal 때문에 임시 kubectl 변경만으로 지속 차단됐다고 가정하지 않는다.
- Argo가 자동 동기화하므로 지속 변경은 Ops 선언에 반영한다. 준비 단계에서는 위 복구 동작도 실행하지 않았다.

작업 근거: Paperclip BIN-14(앱 HTTPS smoke), BIN-15(Ops 인증 준비). 두 업무의 완료는 준비 완료를 뜻하며 운영 배포 완료를 뜻하지 않는다.
