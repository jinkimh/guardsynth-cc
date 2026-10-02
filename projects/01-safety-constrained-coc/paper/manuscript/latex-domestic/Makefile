LATEXMK = latexmk
PYTHON = ../../../runtime/alpamayo/ar1_venv/bin/python

.PHONY: all figures clean

figures:
	$(PYTHON) figures/generate_figures.py

all:
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error main.tex; \
	else \
		xelatex -interaction=nonstopmode -halt-on-error main.tex && \
		bibtex main && \
		xelatex -interaction=nonstopmode -halt-on-error main.tex && \
		xelatex -interaction=nonstopmode -halt-on-error main.tex; \
	fi

clean:
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		$(LATEXMK) -C -xelatex main.tex; \
	else \
		rm -f main.aux main.bbl main.blg main.log main.out main.pdf; \
	fi
