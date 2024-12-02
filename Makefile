BUILDDIR := $(shell ls -d build/cp3* 2>/dev/null | head -n 1)

.PHONY: build clean install test coverage stubs check clean-cov

# https://mesonbuild.com/meson-python/how-to-guides/editable-installs.html
# editable install
install:
	make clean
	git submodule update --init
	uv sync --no-install-project && source .venv/bin/activate
	uv pip install -e . \
		--no-build-isolation \
		--force-reinstall \
		-C=setup-args="-Db_coverage=true" \
		-C=editable-verbose=true

# quick build after having already setup the build directory
build:
	find $(BUILDDIR) -name "*.gcda" -delete
	meson compile -C $(BUILDDIR)

# run tests (calling make install if needed)
test:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. .venv/bin/activate; \
	fi; \
	if [ -z "$(BUILDDIR)" ]; then \
		echo "Build directory not found. Running make install..."; \
		make install; \
	fi; \
	BUILDDIR=$$(ls -d build/cp3* 2>/dev/null | head -n 1); \
	if [ -z "$$BUILDDIR" ]; then \
		echo "Build directory still not found after install. Aborting."; \
		exit 1; \
	fi; \
	meson test -C $$BUILDDIR --verbose

# clean up build artifacts
clean:
	rm -rf build dist builddir
	rm -rf .coverage coverage coverage.info coverage.xml coverage_cpp.xml
	rm -rf .ruff_cache .mypy_cache .pytest_cache
	rm -rf .mesonpy-*
	rm -rf *.gcov

clean-cov:
	find $(BUILDDIR) -name "*.gcda" -exec rm -f {} \;

coverage:
	rm -rf coverage coverage.xml coverage_cpp.xml
	make test
	mkdir coverage
	@if [ -z "$$VIRTUAL_ENV" ]; then . .venv/bin/activate; fi;
	gcovr --filter=src/ --xml coverage_cpp.xml --xml-pretty
	gcovr --filter=src/ --html-details -o coverage/index.html --exclude .venv
	open coverage/index.html

check:
	pre-commit run --all-files --hook-stage manual
