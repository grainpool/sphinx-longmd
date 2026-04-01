SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html"

clean:
	rm -rf "$(BUILDDIR)"

.PHONY: html clean
