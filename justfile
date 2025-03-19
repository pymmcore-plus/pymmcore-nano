env_dir := if os_family() == "windows" { "./.venv/Scripts" } else { "./.venv/bin" }
python := env_dir + if os_family() == "windows" { "/python.exe" } else { "/python3" }
set windows-shell := ["pwsh", "-NoLogo", "-NoProfileLoadTime", "-Command"]
builddir := "builddir"

# install deps and editable package for development
install devices="true" coverage="false" verbose="true":
	uv sync --no-install-project
	uv pip install -e . \
		--no-build-isolation \
		--no-deps \
		--force-reinstall \
		-C=setup-args="-Dbuild_device_adapters={{devices}}" \
		-C=setup-args="-Db_coverage={{coverage}}" \
		-C=setup-args="-Dbuildtype=debugoptimized" \
		-C=build-dir={{builddir}} \
		-C=editable-verbose={{verbose}} -v

# quick build after having already setup the build directory
build:
	meson compile -C {{ builddir }}

# clean up all build artifacts
clean:
	rm -rf build dist {{ builddir }}
	rm -rf .coverage coverage coverage.info coverage.xml coverage_cpp.xml
	rm -rf .ruff_cache .mypy_cache .pytest_cache
	rm -rf .mesonpy-*
	rm -rf *.gcov
	# remove all folders call MMDevice that are INSIDE of a subproject folder
	find -L . -type d -path '*/subprojects/MMDevice' -exec rm -rf {} +
	find -L . -type d -path '*/subprojects/packagecache' -exec rm -rf {} +

	# clean all the nested builddirs
	find src -name builddir -type d -exec rm -rf {} +

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
	{{ python }} scripts/build_stubs.py

# run pre-commit checks
check:
	pre-commit run --all-files --hook-stage manual

pull-mmcore:
	git subtree pull --prefix=src/mmCoreAndDevices https://github.com/micro-manager/mmCoreAndDevices main --squash

# MUST run just version and commit changes before.
release:
	git branch --show-current | grep -q main || (echo "Not on main branch" && exit 1)
	git tag -a v$({{ python }} scripts/extract_version.py) -m "Release v$({{ python }} scripts/extract_version.py)"
	git push upstream --follow-tags

docs-serve:
	uv run --group docs --no-editable --force-reinstall -C=setup-args="-Dmatch_swig=false" mkdocs serve
