from pathlib import Path

from backend.code.analyzer import analyze_structure, parse_dependencies
from backend.code.evidence import SourceIndex
from backend.code.parameters import ParameterExtractor
from backend.code.pipeline import detect_pipeline
from backend.code.python_analysis import analyze_python_file, is_python_file
from backend.code.utils import collect_repository_files

root = Path("tests/fixtures/sample_repo")
files = collect_repository_files(root)
print("files:", [f.path for f in files])
analyses = [a for a in (analyze_python_file(f) for f in files if is_python_file(f)) if a]
for a in analyses:
    print("parsed", a.path, "error:", a.parse_error)
structure = analyze_structure(root, files, analyses)
for d in structure.detected:
    print(f"  {d.path:15s} {d.role.value:24s} {d.confidence}  {d.evidence}")
ex = ParameterExtractor(analyses)
for p in ex.extract():
    print(f"  PARAM {p.name:16s} {p.value!r:28s} {p.file}:{p.line} conf={p.confidence} origin={p.origin}")
print("optimizers:", ex.optimizers())
print("schedulers:", [(s.name, s.file, s.line) for s in ex.schedulers()])
print("losses:", [(s.name, s.file) for s in ex.loss_functions()])
print("metrics:", [(s.name, s.file, s.line) for s in ex.metrics()])
print("deps:", parse_dependencies(root, structure.dependency_manifests))
pipeline = detect_pipeline(analyses, SourceIndex(root))
for s in pipeline.stages:
    print(f"  STAGE {s.name:22s} {s.status.value}")
