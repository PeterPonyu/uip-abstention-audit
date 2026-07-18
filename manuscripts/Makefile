# MT29 manuscript Makefile -- adapted from the reliability-commons paper
# template (v0.1) at
# /home/zeyufu/Desktop/ml-reliability-research/reliability-commons/paper-template/
#
# Targets:
#   make figures  - run every figures/*.R via Rscript (figures regenerate
#                   ONLY from the frozen result JSONs in
#                   ../research/results/MT29/ -- never from hardcoded arrays)
#   make bib      - copy the portfolio shared bibliography next to the paper
#   make paper    - figures + bib, then latexmk -pdf
#   make clean    - remove LaTeX aux files and generated figure PDFs/PNGs

SHARED_BIB ?= /home/zeyufu/Desktop/ml-reliability-research/reliability-commons/shared.bib
R_SCRIPTS  := $(wildcard figures/*.R)

.PHONY: all figures bib paper clean

all: paper

figures:
	@for s in $(R_SCRIPTS); do \
		echo "Rscript $$s"; \
		Rscript "$$s" || exit 1; \
	done
	$(MAKE) -C figures-src

bib:
	@if [ -f "$(SHARED_BIB)" ]; then \
		cp "$(SHARED_BIB)" shared.bib; \
		echo "Copied $(SHARED_BIB) -> shared.bib"; \
	else \
		echo "WARNING: $(SHARED_BIB) not found; creating empty shared.bib"; \
		touch shared.bib; \
	fi

paper: figures bib
	latexmk -pdf -interaction=nonstopmode paper.tex

clean:
	latexmk -C paper.tex 2>/dev/null || true
	rm -f paper.bbl paper.run.xml shared.bib
	rm -f figures/*.pdf figures/*.png
