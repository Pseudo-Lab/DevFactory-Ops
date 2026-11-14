"""Render the checked-in Argo sources offline and validate their PromQL rules."""

from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[2]
# Match the production k3s minor version; no cluster credentials are used.
KUBE_VERSION = "1.32.0"


def run(*args):
    result = subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True)
    print(result.stderr, end="", file=sys.stderr)
    return result.stdout


def resources(documents):
    for resource in documents:
        if not resource:
            continue
        if resource.get("kind") == "List":
            yield from resources(resource["items"])
        else:
            yield resource


def validate():
    chart_count = 0
    rule_count = 0
    paths = set()
    with tempfile.TemporaryDirectory(prefix="ops-ci-") as directory:
        scratch = Path(directory)
        manifests = sorted((ROOT / "apps/prod").rglob("*.yaml"))
        manifests += sorted((ROOT / "clusters").glob("*.yaml"))
        for manifest in manifests:
            app = yaml.safe_load(manifest.read_text())
            if not app or app.get("kind") != "Application":
                continue
            name = app["metadata"]["name"]
            spec = app["spec"]
            sources = spec.get("sources", [spec.get("source", {})])
            if not sources:
                raise ValueError(f"{name}: no application sources")
            for index, source in enumerate(sources):
                rendered = ""
                if "chart" in source:
                    chart_count += 1
                    helm = source.get("helm", {})
                    # Fail rather than silently ignore a newly introduced override.
                    unsupported = set(helm) - {"releaseName", "valueFiles", "values"}
                    if unsupported:
                        raise ValueError(f"{name}: unsupported Helm options: {unsupported}")
                    destination = scratch / f"{name}-{index}"
                    destination.mkdir()
                    print(f"Helm: {name} ({source['chart']} {source['targetRevision']})", flush=True)
                    run("helm", "pull", source["chart"], "--repo", source["repoURL"],
                        "--version", str(source["targetRevision"]), "--untar",
                        "--untardir", str(destination))
                    chart = str(destination / source["chart"])
                    options = ["--namespace", spec["destination"]["namespace"],
                               "--kube-version", KUBE_VERSION]
                    for value_file in helm.get("valueFiles", []):
                        if not value_file.startswith("$values/"):
                            raise ValueError(f"{name}: expected repository $values path: {value_file}")
                        if not any(s.get("ref") == "values" and
                                   s.get("repoURL") == "https://github.com/Pseudo-Lab/DevFactory-Ops.git"
                                   for s in sources):
                            raise ValueError(f"{name}: $values requires this repository's ref: values source")
                        options += ["--values", str(ROOT / value_file.removeprefix("$values/"))]
                    if "values" in helm:
                        inline = destination / "inline-values.yaml"
                        inline.write_text(helm["values"])
                        options += ["--values", str(inline)]
                    print(run("helm", "lint", chart, *options), end="", flush=True)
                    rendered = run("helm", "template", helm.get("releaseName", name), chart, *options)
                elif "path" in source:
                    path = ROOT / source["path"]
                    if not path.is_dir():
                        raise ValueError(f"{name}: missing source directory: {source['path']}")
                    if path in paths:
                        continue
                    paths.add(path)
                    if any((path / filename).is_file() for filename in
                           ("kustomization.yaml", "kustomization.yml", "Kustomization")):
                        print(f"Kustomize: {source['path']}", flush=True)
                        rendered = run("kustomize", "build", "--enable-helm", str(path))
                    else:
                        print(f"YAML directory: {source['path']}", flush=True)
                        rendered = "\n".join("---\n" + file.read_text() for file in sorted(path.iterdir())
                                             if file.suffix in {".yaml", ".yml", ".json"})
                elif "ref" not in source:
                    raise ValueError(f"{name}: source requires chart, path or values ref")
                for resource in resources(yaml.safe_load_all(rendered)):
                    if not resource or resource.get("kind") not in {"VMRule", "PrometheusRule"}:
                        continue
                    groups = resource["spec"]["groups"]
                    if resource["kind"] == "VMRule":
                        # vmalert query/evaluation options are not Prometheus rule syntax.
                        # Strip only these known extensions; keep other fields strict.
                        groups = [{key: value for key, value in group.items()
                                   if key not in {"params", "concurrency"}}
                                  for group in groups]
                    rule_count += sum(len(group["rules"]) for group in groups)
                    rules = scratch / f"{name}-{resource['metadata']['name']}-rules.yaml"
                    rules.write_text(yaml.safe_dump({"groups": groups}))
                    print(run("promtool", "check", "rules", str(rules)), end="", flush=True)
        if not chart_count or not rule_count:
            raise ValueError("Expected Helm charts and monitoring rules; refusing an empty check")
        print(f"Validated {chart_count} Helm applications and {rule_count} monitoring rules")


if __name__ == "__main__":
    try:
        validate()
    except subprocess.CalledProcessError as error:
        print(error.stdout, end="")
        print(error.stderr, end="")
        raise SystemExit(error.returncode)
