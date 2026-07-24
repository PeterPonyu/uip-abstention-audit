# MT29 manuscript build.
#
# Targets:
#   make figures  - regenerate figures from frozen result JSONs
#   make bib      - verify the tracked shared bibliography
#   make paper    - figures + bibliography check + LaTeX build
#   make clean    - remove LaTeX auxiliaries and generated figures

R_SCRIPTS := $(wildcard figures/*.R)

.PHONY: all figures bib paper clean

all: paper

figures:
	@for s in $(R_SCRIPTS); do \
		echo "Rscript $$s"; \
		Rscript "$$s" || exit 1; \
	done
	$(MAKE) -C figures-src

bib:
	@test -s shared.bib || { echo "ERROR: tracked manuscripts/shared.bib is missing or empty"; exit 1; }
	@echo "Using tracked manuscripts/shared.bib"

paper: figures bib
	latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex

clean:
	latexmk -C paper.tex 2>/dev/null || true
	rm -f paper.bbl paper.run.xml
	rm -f figures/*.pdf figures/*.png
