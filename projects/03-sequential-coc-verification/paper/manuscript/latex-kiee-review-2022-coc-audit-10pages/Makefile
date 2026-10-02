LATEXMK = latexmk
TEX_CACHE = $(CURDIR)/.texlive-cache
TEX_LOCAL = $(CURDIR)/.texlive-local
TEX_ENV = env TEXINPUTS=$(TEX_LOCAL)/tex//: TEXMFVAR=$(TEX_CACHE)
LUALATEX = $(TEX_ENV) lualatex

.PHONY: all test clean

test:
	python3 -m unittest -v tests/test_kiee_format.py tests/test_korean_editorial_integrity.py

all: test
	@mkdir -p $(TEX_CACHE)
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		$(TEX_ENV) $(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error main.tex; \
	else \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		$(TEX_ENV) bibtex main && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex; \
	fi

clean:
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -C -lualatex main.tex; \
	else \
		rm -f main.aux main.bbl main.blg main.log main.out main.pdf; \
	fi
