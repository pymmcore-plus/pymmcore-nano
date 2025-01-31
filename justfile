env_dir := if os_family() == "windows" { "./.venv/Scripts" } else { "./.venv/bin" }
python := env_dir + if os_family() == "windows" { "/python.exe" } else { "/python3" }
builddir := `ls -d build/cp3* 2>/dev/null | head -n 1`

# install deps and editable package for development
install:
	rm -rf build dist builddir
	uv sync --no-install-project
	uv pip install -e . \
		--no-build-isolation \
		--no-deps \
		--force-reinstall \
		# -C=setup-args="-Db_coverage=true" \
		# -C=setup-args="-Dhold_gil=true" \
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

build-devices:
	just build-adapter DemoCamera
	just build-adapter Utilities
	# just build-adapter SequenceTester

build-mmdevice:
	meson setup src/mmCoreAndDevices/MMDevice/builddir src/mmCoreAndDevices/MMDevice
	meson compile -C src/mmCoreAndDevices/MMDevice/builddir

build-adapter dir:
	just build-mmdevice
	mkdir -p src/mmCoreAndDevices/DeviceAdapters/{{dir}}/subprojects
	rm -f src/mmCoreAndDevices/DeviceAdapters/{{dir}}/subprojects/MMDevice
	ln -s ../../../MMDevice src/mmCoreAndDevices/DeviceAdapters/{{dir}}/subprojects/MMDevice

	meson setup src/mmCoreAndDevices/DeviceAdapters/{{dir}}/builddir src/mmCoreAndDevices/DeviceAdapters/{{dir}}
	meson compile -C src/mmCoreAndDevices/DeviceAdapters/{{dir}}/builddir

	# # copy to tests dir...
	# # this is made annoying because the extension is platform dependent and needs to be just right for
	# # micromanager to pick it up
	# file=$(find src/mmCoreAndDevices/DeviceAdapters/{{dir}}/builddir -type f -name 'libmmgr_dal_*' ! -name '*.p*') && \
	# filename=$(basename "$file" | sed 's/\.[^.]*$//') && \
	# cp "$file" "tests/adapters/$filename"

# MUST run just version and commit changes before.
release:
	git branch --show-current | grep -q main || (echo "Not on main branch" && exit 1)
	git tag -a v$({{ python }} scripts/extract_version.py) -m "Release v$({{ python }} scripts/extract_version.py)"
	git push upstream --follow-tags
