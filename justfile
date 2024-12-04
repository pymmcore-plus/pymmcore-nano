env_dir := if os_family() == "windows" { "./.venv/Scripts" } else { "./.venv/bin" }
python := env_dir + if os_family() == "windows" { "/python.exe" } else { "/python3" }
builddir := `ls -d build/cp3* 2>/dev/null | head -n 1`

# install deps and editable package for development
install:
	git submodule update --init
	uv sync --no-install-project
	uv pip install -e . \
		--no-build-isolation \
		--no-deps \
		--force-reinstall \
		-C=setup-args="-Db_coverage=true" \
		-C=setup-args="-Dbuildtype=debugoptimized" \
		-C=editable-verbose=true -v

# quick build after having already setup the build directory
build:
	meson compile -C {{ builddir }}

# clean up all build artifacts
clean:
	rm -rf build dist builddir
	rm -rf .coverage coverage coverage.info coverage.xml coverage_cpp.xml
	rm -rf .ruff_cache .mypy_cache .pytest_cache
	rm -rf .mesonpy-*
	rm -rf *.gcov

# run tests
test:
	if [ -z {{ builddir }} ]; then just install; fi
	{{ python }} -m pytest -v --color=yes

# run tests with coverage
test-cov:
	rm -rf coverage coverage.xml coverage_cpp.xml
	{{ python }} -m pytest -v --color=yes --cov --cov-report=xml
	gcovr --filter=src/mmCoreAndDevices/MMCore/MMCore.cpp --xml coverage_cpp.xml -s

# clean up coverage artifacts
clean-cov:
	find {{ builddir }} -name "*.gcda" -exec rm -f {} \;

# update version in meson.build
version:
	meson rewrite kwargs set project / version $({{ python }} scripts/extract_version.py)

# run pre-commit checks
check:
	pre-commit run --all-files --hook-stage manual

