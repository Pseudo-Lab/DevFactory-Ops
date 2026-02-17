# 🚀 Project Onboarding & Setup Guide

이 문서는 Oracle Cloud (OCI) 가입부터 k3s 클러스터 구축 및 GitOps 가동까지의 전체 과정을 단계별로 안내합니다.

---

## 🏛️ 설계 철학 (Architecture Philosophy)

이 프로젝트는 **"완전한 복구성(Resilience)"**과 **"관심사의 분리(Separation of Concerns)"**를 핵심 원칙으로 합니다.

1.  **L1: 인프라 (Terraform)** - VM, 네트워크 등 기초 공사만 담당합니다. 소프트웨어 설치 로직을 최소화하여 인프라 변경 시 서버가 재시작되거나 삭제되는 위험을 방지합니다.
2.  **L2: 부트스트랩 (Bootstrap Script)** - OS 방화벽, k3s 클러스터 엔진, ArgoCD를 설치합니다. 테라폼으로부터 독립되어 있어 클러스터만 따로 초기화하거나 복구할 때 유용합니다.
3.  **L3: 플랫폼 & 앱 (GitOps)** - ArgoCD가 모든 것을 관리합니다. Git의 매니페스트가 클러스터의 상태 그 자체가 됩니다.

---

## 🏗️ 1단계: OCI 계정 준비 및 API 설정

1.  **OCI 계정 가입**: [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)에 가입합니다.
2.  **구획(Compartment) 생성**: (로그인 후) `Identity & Security` > `Compartments`에서 프로젝트용 구획을 생성하고 `OCID`를 복사해둡니다.
3.  **API 키 생성**:
    - `User Settings` > `API Keys` > `Add API Key` 클릭.
    - 프라이빗 키와 퍼블릭 키를 다운로드합니다.
    - 다운로드한 프라이빗 키(`.pem`)는 프로젝트의 `terraform/` 디렉토리에 저장합니다 (예: `prod.pem`).
    - 생성된 설정 정보를 복사하여 `terraform/oci/prod/terraform.tfvars` 작성 시 사용합니다.

---

## 🔐 2단계: Terraform 초기 설정 (IaC)

1.  **환경 변수(`tfvars`) 작성**: 
    - `terraform/oci/prod/terraform.tfvars.example`을 복제하여 `terraform.tfvars`를 생성합니다.
    - 위에서 얻은 `tenancy_ocid`, `user_ocid`, `fingerprint`, `compartment_id`, `private_key_path`를 입력합니다.
2.  **백엔드(Object Storage) 설정**:
    - OCI 콘솔에서 `terraform-state-prod` 버킷을 생성합니다.
    - `backend.tf` 파일의 `namespace` 등을 본인의 계정 정보에 맞게 수정합니다.
3.  **초기화 및 배포**:
    ```bash
    cd terraform/oci/prod
    terraform init
    terraform apply
    ```
    *주의: 인프라 생성 후 할당된 공인 IP를 확인해두세요.*

---

## 🎡 3단계: 클러스터 부트스트랩 (k3s)

인프라가 준비되면, 서버에 접속하여 클러스터 엔진을 설치합니다.

1.  **리포지토리 클론**:
    - 서버에 접속하여 작업 디렉토리로 이동한 뒤 리포지토리를 클론합니다.
    ```bash
    git clone https://github.com/Pseudo-Lab/DevFactory-Ops.git
    cd DevFactory-Ops
    ```

2.  **부트스트랩 스크립트 실행**:
    - 필요한 경우 `export`를 통해 설정을 변경한 뒤 스크립트를 실행합니다.
    ```bash
    # (선택) 외부(로컬 PC)에서 kubectl 명령어를 사용하고 싶은 경우에만 지정합니다.
    # 서버 내부에서만 작업한다면 생략해도 무방합니다.
    export LB_IP="실제_LB_IP_또는_공인_IP"

    # 부트스트랩 스크립트 실행
    bash scripts/bootstrap-cluster.sh
    ```
    *이 스크립트는 다음 과정을 자동으로 수행합니다:*
    - **OS 방화벽 개방**: 6443, 80, 443 등 필수 포트 허용
    - **k3s & Helm 설치**: 검증된 특정 버전으로 설치 및 고정
    - **Kubeconfig 자동 설정**: `~/.kube/config` 생성 및 권한 부여
    - **사용자 편의 설정**: `k` 단축키(alias) 및 명령어 자동 완성(bash-completion) 등록
    - **ArgoCD 배포**: GitOps 엔진 가동 및 Root Application 등록

---

## 🐙 4단계: GitOps 활성화 (ArgoCD)

클러스터가 준비되면, 모든 앱과 플랫폼 구성을 리포지토리(Git)와 동기화합니다.

1.  **원격(로컬) 접속 설정**:
    - 서버의 `~/.kube/config` 파일을 로컬 PC의 `~/.kube/config`로 가져옵니다.
    - 파일 내 `server` 주소를 `https://<LB_IP_또는_Instance_IP>:6443`으로 수정합니다.
2.  **GitOps 동기화 확인**:
    - 스크립트가 자동으로 `clusters/prod.yaml`을 적용했습니다.
    - 이제 ArgoCD가 리포지토리를 감시하며 `ingress-nginx`, `sealed-secrets` 등을 자동으로 배포합니다.
3.  **동기화 확인**:
    - ArgoCD UI에 접속하여 `ingress-nginx`, `sealed-secrets` 등이 자동으로 배포되는지 확인합니다.

---

## 🛠️ 운영 및 관리 규칙

- **형상 관리**: 모든 인프라 변경은 `terraform/` 코드로, K8s 변경은 `kubernetes/` 매니페스트를 통해 PR 및 머지 후 반영합니다.
- **보안**: 비밀번호나 키 등은 절대 Git에 커밋하지 않으며, 반드시 `Sealed Secrets`를 사용하여 암호화된 상태로 커밋합니다.
- **방화벽**: 서버의 OS 방화벽(`iptables`) 규칙 변경 시 `iptables-persistent`를 통해 영구 저장해야 합니다.

---

> [!TIP]
> **성공 여부 확인**: `kubectl get nodes` 명령어로 노드가 `Ready` 상태이고, `kubectl get pods -A`에서 모든 시스템 포드가 `Running`인 경우 정상입니다.
