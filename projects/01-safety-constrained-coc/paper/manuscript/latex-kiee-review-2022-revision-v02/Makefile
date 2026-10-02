ROOT := $(abspath ../../../../..)
OUT := $(ROOT)/artifacts/projects/safety-constrained-coc/public/kiee-review-002/revision-2026-09-30-001
TEX_CACHE := $(OUT)/texlive-cache
LUALATEX := env TEXMFVAR=$(TEX_CACHE) lualatex -interaction=nonstopmode -halt-on-error -output-directory=$(OUT)

.PHONY: all manuscript rebuttal
all: manuscript rebuttal

manuscript:
	@mkdir -p $(OUT) $(TEX_CACHE)
	$(LUALATEX) main.tex
	cd $(OUT) && env BIBINPUTS=$(CURDIR): bibtex main
	$(LUALATEX) main.tex
	$(LUALATEX) main.tex
	cp $(OUT)/main.pdf main.pdf

rebuttal:
	@mkdir -p $(OUT) $(TEX_CACHE)
	$(LUALATEX) response-to-reviewer-1.tex
	$(LUALATEX) response-to-reviewer-1.tex
	cp $(OUT)/response-to-reviewer-1.pdf response-to-reviewer-1.pdf
