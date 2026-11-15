# Bingo 개발 Supabase DB 점검

## 범위와 상태 — 2026-11-16

- 개발 Supabase 프로젝트 `dev`에 `public.bingo_monitor_health()` 적용 완료.
- 기존 개발 anon 키로 실제 RPC 응답 `HTTP 200`, JSON 숫자 `1` 확인.
- 키 교체 없음. `/rest/v1/` 루트의 401은 키가 무효라는 뜻이 아니었으며,
  점검 대상은 `/rest/v1/rpc/bingo_monitor_health`다.
- Gatus 설정과 SealedSecret 준비 및 검증 완료. main 반영과 운영 활성화는 아직 미실행.
- 운영 DB 점검 및 기존 Discord 설정 변경 없음.

## 구성

운영 클러스터의 public Gatus가 개발 Supabase Data API를 6시간마다 호출한다.
개발 애플리케이션이나 프리뷰 서버가 실행 중일 필요는 없다.
15초 이내 HTTP 200과 본문 `1`을 모두 만족해야 성공이다.
실패 1회에 장애 알림, 성공 1회에 복구 알림을 기존 Discord 경로로 보낸다.

DB 함수는 `SELECT 1`만 수행한다. 업무 데이터를 읽거나 변경하지 않으며,
애플리케이션 테이블, RLS 정책, 마이그레이션 상태까지 검증하지 않는다.
무료 프로젝트의 자동 일시정지 방지를 보장하지 않는다.

- 함수 원본: [개발 전용 SQL](../scripts/ops/sql/bingo-dev-db-health.sql)
- Gatus endpoint: `infrastructure/overlays/prod/monitoring/gatus/public/configmap.yaml`
- 환경 변수 연결: 같은 디렉터리의 `kustomization.yaml` (public Deployment에만 적용)
- Secret: `monitoring/bingo-dev-db-monitor`
- 암호화 파일: `infrastructure/overlays/prod/monitoring/gatus/bingo-dev-db-monitor-sealed-secret.yaml`

함수는 SECURITY INVOKER, STABLE이며 search_path를 비운다.
PUBLIC 및 authenticated 실행 권한은 없고 anon에만 명시적으로 실행 권한을 부여한다.
다른 함수의 권한이나 기본 권한은 변경하지 않는다.
SQL은 CREATE만 사용하므로 이미 적용된 DB에서 재실행하지 않는다.

개발 URL과 anon 키는 기존 보호된 설정에서 읽어 클러스터의 활성 공개 인증서로
strict scope(name/namespace 고정) 암호화했다. 일반 Secret과 키 원문은 Git에 넣지 않는다.
Supabase 관리 토큰은 함수 적용에만 사용하며 Gatus에 전달하지 않는다.

## 검증 결과

- 실제 개발 RPC: 기존 apikey만 사용하여 200/1. API 키 없이는 401.
- DB 함수 정의, STABLE, SECURITY INVOKER, anon/authenticated 권한 확인.
- 운영과 동일한 Gatus 이미지 digest `98e144a6fccc066152912b500c55677ab3442c1a54806be587190afe008adf4c` 검증.
- 로컬 mock HTTP: 200/1 성공, 200/2 실패, 401 실패, 타임아웃 실패.
- mock 검증에서는 주기를 줄였으며 운영 설정의 6h/15s 값은 별도로 확인.
- mock 테스트에서는 Discord 발송을 끄고 실제 채널에 요청하지 않음.
- Kustomize 렌더링 및 public Deployment의 Secret/ConfigMap 참조 확인.
- 운영 Kubernetes API의 server dry-run 통과. 리소스 적용은 하지 않음.

## 반영 후 확인

승인된 PR/main 반영 후 기존 GitOps 배포를 확인한다. 수동 배포를 중복 실행하지 않는다.
SealedSecret 복호화와 Secret 생성, Gatus rollout, 최초 개발 점검 성공,
기존 운영 점검 정상 여부를 확인한다. 다음 6시간 주기 결과는 별도 확인 후 기록한다.
실제 Discord 장애·복구 전달은 이번 작업에서 아직 재검증하지 않았다.

Secret과 endpoint/env 연결을 함께 반영해야 한다. 필수 Secret이 없으면 Gatus가 시작하지 못한다.
문제가 생기면 개발 endpoint와 public Deployment의 추가 env 참조를 함께 되돌린다.
기존 운영 DB 점검은 유지한다. 사용하지 않는 개발 함수/Secret의 삭제는 별도 판단한다.

참고: [Gatus 설정](https://github.com/TwiN/gatus),
[Supabase DB 함수와 권한](https://supabase.com/docs/guides/database/functions),
[Supabase 관리 API 쿼리](https://supabase.com/docs/reference/api/v1-run-a-query).
