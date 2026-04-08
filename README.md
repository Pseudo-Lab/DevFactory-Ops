# DevFactory-Ops

OCI 위에서 k3s + ArgoCD로 운영되는 인프라 관리 리포지토리입니다.

---

## 🏛️ 설계 철학 (Architecture Philosophy)

이 리포지토리는 **완전한 복구성** (Resilience)과 **관심사의 분리** (Separation of Concerns)를 핵심 원칙으로 합니다.

1.  **L1: 인프라 (Terraform)** - VM, 네트워크 등 기초 공사만 담당합니다. 소프트웨어 설치 로직을 최소화하여 인프라 변경 시 서버가 재시작되거나 삭제되는 위험을 방지합니다.
2.  **L2: 부트스트랩 (Bootstrap Script)** - OS 방화벽, k3s 클러스터 엔진, ArgoCD를 설치합니다. 테라폼으로부터 독립되어 있어 클러스터만 따로 초기화하거나 복구할 때 유용합니다.
3.  **L3: 플랫폼 & 앱 (GitOps)** - ArgoCD가 모든 것을 관리합니다. Git의 매니페스트가 클러스터의 상태 그 자체가 됩니다.
4.  **L4: 자동화 (CI/CD Pipeline)** - 서비스 리포지토리와 Ops 리포지토리가 협력하여 배포를 자동화합니다.

---

## 🌐 네트워크 구조

```
브라우저
  ↓ :80 / :443
OCI Load Balancer (devfactory-prod-lb)
  ├── :80  → NodePort 30080
  └── :443 → NodePort 30443  ← TCP Passthrough (TLS 미종료)
               ↓
               K8s nginx ingress
                 - cert-manager가 Let's Encrypt 인증서 발급·갱신
                 - HTTP → HTTPS 리다이렉트
                 - 도메인 + 경로 기반 라우팅
```

> **주의**: OCI LB는 443을 TCP Passthrough로 넘기므로 TLS는 K8s nginx ingress + cert-manager가 담당합니다.
> K8s ingress 작성 시 `cert-manager.io/cluster-issuer: letsencrypt-prod` annotation과 `tls` 블록이 **반드시 필요**합니다.
> 자세한 내용은 [docs/networking.md](docs/networking.md)를 참조하세요.

---

## 🐙 GitOps 구조 (App of Apps)

ArgoCD는 **App of Apps 패턴**으로 구성되어 있습니다.

```
clusters/prod.yaml  (root-app)
  └── apps/prod/
        ├── infrastructure.yaml  →  argocd, cert-manager, ingress-nginx,
        │                           sealed-secrets, victoria-metrics, monitoring
        └── services.yaml        →  homepage, event-bingo, experiment-platform
```

- `clusters/prod.yaml`을 클러스터에 적용하면 나머지는 ArgoCD가 자동으로 모두 배포
- 모든 App은 `automated sync + selfHeal + prune` 활성화 (Git이 곧 클러스터 상태)
- 새 서비스 추가 시 `apps/prod/services/`에 ArgoCD Application 파일만 추가하면 됨

---

## 🛠️ 운영 및 관리 규칙

- **형상 관리**: 모든 인프라 변경은 `terraform/` 코드로, K8s 변경은 `kubernetes/` 매니페스트를 통해 PR 및 머지 후 반영합니다.
- **보안**: 비밀번호나 키 등은 절대 Git에 커밋하지 않으며, 반드시 `Sealed Secrets`를 사용하여 암호화된 상태로 커밋합니다.
- **방화벽**: 서버의 OS 방화벽(`iptables`) 규칙 변경 시 `iptables-persistent`를 통해 영구 저장해야 합니다.

---

## 📚 문서

- [인프라 셋업 가이드](docs/setup.md) — OCI 계정 준비, Terraform, k3s 부트스트랩, ArgoCD 활성화
