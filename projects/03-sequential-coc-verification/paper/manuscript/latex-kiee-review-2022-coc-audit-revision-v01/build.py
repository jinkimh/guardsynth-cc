"""Build the article and responses beside their manuscript sources."""
from pathlib import Path
import os
import re
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
NAMES = ("main", "main-clean", "response-to-reviewer-1", "response-to-reviewer-2", "response-to-reviewer-3")

def build(names):
    env = os.environ.copy()
    env.update(TEXINPUTS=str(SOURCE / ".texlive-local/tex") + "//:" + str(SOURCE) + "//:",
               BIBINPUTS=str(SOURCE) + ":", BSTINPUTS=str(SOURCE) + ":",
               TEXMFVAR=str(SOURCE / ".texlive-cache"))
    responses_prepared = False
    for name in names:
        if name not in NAMES:
            raise ValueError("Unknown document: " + name)
        if name.startswith("response-") and not responses_prepared:
            subprocess.run([sys.executable, "-B", "sync_responses.py"], cwd=SOURCE, check=True)
            subprocess.run([sys.executable, "-B", "verify_documents.py", "--locate"], cwd=SOURCE, check=True)
            responses_prepared = True
        latex = ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", name + ".tex"]
        commands = [latex]
        if name.startswith("main"):
            commands.append(["bibtex", name])
        commands.extend([latex, latex])
        for index, command in enumerate(commands, 1):
            log = SOURCE / (name + "-build-" + str(index) + ".txt")
            with log.open("w") as stream:
                result = subprocess.run(command, cwd=SOURCE, env=env, stdout=stream, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(log.read_text()[-6500:])
        if name == "main":
            locations = ["% Generated from current manuscript auxiliary labels."]
            for match in re.finditer(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{([^}]+)\}", (SOURCE / "main.aux").read_text()):
                key, number, page = match.groups()
                if key.startswith(("sec:", "tab:", "eq:", "lst:", "fig:")):
                    kind = {"sec": "절", "tab": "표", "eq": "식", "lst": "목록", "fig": "그림"}[key.split(":")[0]]
                    label = number + kind + "(" + page + "쪽)" if kind == "절" else kind + " " + number + "(" + page + "쪽)"
                    locations.append(r"\expandafter\def\csname mloc@" + key + r"\endcsname{" + label + "}")
            (SOURCE / "manuscript-locations.tex").write_text("\n".join(locations) + "\n")
        print(name + " built", flush=True)
    if set(NAMES).issubset(names):
        subprocess.run([sys.executable, "-B", "verify_documents.py"], cwd=SOURCE, check=True)

if __name__ == "__main__":
    build(sys.argv[1:] or NAMES)
