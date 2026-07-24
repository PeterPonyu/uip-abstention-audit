# Standalone TikZ figure sources (protocol schematics, not data-driven R plots).
# Each fig*.tex is a self-contained `standalone` document; `make` compiles every
# one with pdflatex and copies the result into ../figures/ so \includegraphics
# in the manuscript resolves it via the existing \graphicspath{{figures/}}.

TEX_SOURCES := $(wildcard fig*.tex)
PDFS        := $(TEX_SOURCES:.tex=.pdf)
DEST_DIR    := ../figures

.PHONY: all clean

all: $(addprefix $(DEST_DIR)/,$(PDFS))

$(DEST_DIR)/%.pdf: %.pdf
	@mkdir -p $(DEST_DIR)
	cp $< $@

%.pdf: %.tex
	pdflatex -interaction=nonstopmode -halt-on-error $< >/dev/null
	pdflatex -interaction=nonstopmode -halt-on-error $< >/dev/null

clean:
	rm -f *.aux *.log *.pdf
