# Run from this directory: make
# Keep the working PDF and auxiliary files beside main.tex.
JOB = ncaa-manuscript-en
# Optional local dependencies for the minimal TeX Live installation.
export TEXINPUTS := $(CURDIR)/.texlive-local//:$(TEXINPUTS)
export TEXMFVAR := $(CURDIR)/.texlive-cache

.PHONY: all
all:
	pdflatex -interaction=nonstopmode -halt-on-error -jobname=$(JOB) $(JOB).tex
	bibtex "$(JOB)"
	pdflatex -interaction=nonstopmode -halt-on-error -jobname=$(JOB) $(JOB).tex
	pdflatex -interaction=nonstopmode -halt-on-error -jobname=$(JOB) $(JOB).tex
	pdflatex -interaction=nonstopmode -halt-on-error supplementary-information.tex
	pdflatex -interaction=nonstopmode -halt-on-error supplementary-information.tex
