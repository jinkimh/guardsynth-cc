LATEXMK = latexmk

.PHONY: all clean

all:
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error main.tex

clean:
	$(LATEXMK) -C -xelatex main.tex
