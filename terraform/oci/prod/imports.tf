# #############################################################################
# [기존 리소스 가져오기 (Import)]
# 기존에 수동으로 생성된 운영계 리소스를 테라폼 관리 대상으로 편입합니다.
# #############################################################################

# 1. VCN
import {
  to = oci_core_vcn.prod_vcn
  id = "ocid1.vcn.oc1.ap-chuncheon-1.amaaaaaa7rlw6kaam6u523nqzl4l4urgflqnccy4hemezdeshfyn5zfggbla"
}

# 2. Subnet
import {
  to = oci_core_subnet.prod_subnet
  id = "ocid1.subnet.oc1.ap-chuncheon-1.aaaaaaaazrjpegygezejzytqi2z6kd5reacfsrtn3klsvluleqr53kqhzrqa"
}

# 3. Compute Instance
import {
  to = oci_core_instance.prod_instance
  id = "ocid1.instance.oc1.ap-chuncheon-1.an4w4ljr7rlw6kacaz47ncs6ci7m7a7umwbt5fmh6t3ntxxiatzxadxoh6jq"
}
