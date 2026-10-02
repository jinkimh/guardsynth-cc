LATEXMK = latexmk
PYTHON = ../../../third_party/cascade-devkit/.venv/bin/python
TEX_CACHE = $(CURDIR)/.texlive-cache
LUALATEX = env TEXMFVAR=$(TEX_CACHE) lualatex
MPL_CACHE = $(CURDIR)/.matplotlib-cache

.PHONY: all figures test clean

figures:
	@mkdir -p $(MPL_CACHE)
	env MPLCONFIGDIR=$(MPL_CACHE) $(PYTHON) figures/generate_figures.py

test:
	python3 -m unittest discover -v -s tests

all: test
	@mkdir -p $(TEX_CACHE)
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error main.tex; \
	else \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		bibtex main && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex; \
	fi

clean:
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -C -lualatex main.tex; \
	else \
		rm -f main.aux main.bbl main.blg main.log main.out main.pdf; \
	fi
