## 📌 프로젝트 개요

- **목표:** Docker Compose → k3s + ArgoCD + Sealed Secrets + Nginx Ingress + OCI LB 이관
- **핵심 가치:** 유지보수 편의성, 표준화, 가용성 향상
- **주요 인프라:** Oracle A1 (Prod / Dev 분리 운영)
- **리포지토리:** `Pseudo-Lab/DevFactory-Ops`

---

## 🏗️ 리포지토리 표준 구조 (DevFactory-Ops)

```
DevFactory-Ops/
├── terraform/oci/       # L1/L2: OCI 리소스 (LB, 네트워크, 서버)
│   ├── dev/             # 개발계 환경 설정
│   └── prod/            # 운영계 환경 설정
├── kubernetes/platform/ # L3: 공통 컨트롤러 (Ingress, ArgoCD, SealedSecrets)
├── kubernetes/apps/     # L4: 개별 서비스 매니페스트
└── kubernetes/clusters/ # 클러스터별 최종 상태 정의 (App-of-Apps)
```

---

## 📅 단계별 체크리스트

### Phase 0: Terraform 기초 인프라화 (IaC) [ ]

- [ ]  OCI API 키 생성 및 접속 환경 구성 (Prod/Dev 멀티 계정)
- [ ]  OCI Object Storage 버킷 생성 및 Terraform Remote State(Backend) 설정
- [ ]  기존 A1 리소스(VCN, Instance) Import 및 관리 코드 작성
- [ ]  OCI Flexible Load Balancer (10Mbps Always Free) 생성 코드 작성 및 배포

### Phase 1: k3s 클러스터 및 플랫폼 레이어 안착 [ ]

- [ ]  k3s 설치 (options: `--disable traefik --disable servicelb`)
- [ ]  Nginx Ingress Controller 설치 (via Helm, NodePort 30080/30443)
- [ ]  ArgoCD (Non-HA) 설치 및 외부 노출 (via Ingress)
- [ ]  Sealed Secrets Controller 설치 및 `kubeseal` 환경 구성

### Phase 2: 파일럿 서비스 이관 (Test Bed) [ ]

- [ ]  대상 앱: `df-getcloser`
- [ ]  `DevFactory-Ops` 리포지토리에 K8s 매니페스트(Deploy, Svc, Ing) 작성
- [ ]  ArgoCD에 애플리케이션 등록 및 배포 확인
- [ ]  OCI LB 트래픽을 Docker(80) → k3s(30080)로 단계적 전환 테스트
- [ ]  SSL 적용 확인 (Cert-manager 연동)

### Phase 3: 전체 서비스 순차 이관 [ ]

- [ ]  모니터링: `VictoriaMetrics`(DB) + `Grafana`(Dashboard) 및 `Gatus`(Status Page) 설치
- [ ]  핵심 서비스: `df-cert`, `JobPT` 순차 이관
- [ ]  데이터: PostgreSQL 데이터 백업 및 k3s PVC 마이그레이션
- [ ]  전체 데이터에 대한 주기적 외부 백업 체계 가동

### Phase 4: 최종 최적화 및 레거시 정리 [ ]

- [ ]  기존 Docker 컨테이너 및 엔진 완전 중지/삭제
- [ ]  k3s Nginx Ingress가 호스트의 80, 443 포트를 직접 점유하도록 최종 변경
- [ ]  보안 그룹(Security List) 재정비 및 성능 튜닝
- [ ]  운영 매뉴얼 최종 업데이트

---

## 🔒 보안 및 운영 정책

- **Secrets:** raw 시크릿은 절대 Git에 커밋하지 않음. 반드시 `Sealed Secrets` 사용.
- **GitOps:** 모든 변경 사항은 `DevFactory-Ops` 리포지토리의 PR 및 머지를 통해 반영.
- **가시성:** `Grafana`로 리소스 모니터링, `Gatus`로 서비스 상태 공유, `ArgoCD`로 실시간 로그 확인.

---

## 📊 히스토리 및 메모

- **2026-02-12:** 마스터 플랜(v1.0) 수립. OCI LB 및 k3s 도입 결정.
- **2026-02-13:** 마스터 플랜(v1.1) 업데이트. Phase 0(Terraform) 상세화 및 Remote State 전략 추가.