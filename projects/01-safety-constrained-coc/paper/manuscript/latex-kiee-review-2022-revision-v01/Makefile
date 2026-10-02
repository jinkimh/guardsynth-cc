LATEXMK = latexmk
TEX_CACHE = $(CURDIR)/.texlive-cache
LUALATEX = env TEXMFVAR=$(TEX_CACHE) lualatex
DOCUMENTS = main response-to-reviewers response-to-reviewer-2

.PHONY: all manuscript rebuttal rebuttal-reviewer-2 clean

all: manuscript rebuttal

manuscript:
	@mkdir -p $(TEX_CACHE)
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error main.tex; \
	else \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		bibtex main && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error main.tex; \
	fi

rebuttal:
	@mkdir -p $(TEX_CACHE)
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error response-to-reviewers.tex; \
	else \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error response-to-reviewers.tex && \
		$(LUALATEX) -interaction=nonstopmode -halt-on-error response-to-reviewers.tex; \
	fi

rebuttal-reviewer-2:
	@mkdir -p $(TEX_CACHE)
	$(LUALATEX) -interaction=nonstopmode -halt-on-error response-to-reviewer-2.tex
	$(LUALATEX) -interaction=nonstopmode -halt-on-error response-to-reviewer-2.tex

clean:
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		for document in $(DOCUMENTS); do \
			env TEXMFVAR=$(TEX_CACHE) $(LATEXMK) -C -lualatex $$document.tex; \
		done; \
	else \
		rm -f $(foreach document,$(DOCUMENTS),$(document).aux $(document).bbl $(document).blg $(document).fdb_latexmk $(document).fls $(document).log $(document).out $(document).pdf); \
	fi
