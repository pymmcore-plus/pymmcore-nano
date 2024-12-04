env_dir := if os_family() == "windows" { "./.venv/Scripts" } else { "./.venv/bin" }
python := env_dir + if os_family() == "windows" { "/python.exe" } else { "/python3" }
builddir := `ls -d build/cp3* 2>/dev/null | head -n 1`

# install deps and editable package for development
install:
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

# run pre-commit checks
check:
	pre-commit run --all-files --hook-stage manual

pull-mmcore:
	git subtree pull --prefix=src/mmCoreAndDevices https://github.com/micro-manager/mmCoreAndDevices main --squash

build-devices:
	just build-democamera
	just build-utilities
	# just build-sequencetester

build-mmdevice:
	meson setup src/mmCoreAndDevices/MMDevice/builddir src/mmCoreAndDevices/MMDevice
	meson compile -C src/mmCoreAndDevices/MMDevice/builddir

build-democamera:
	just build-mmdevice
	mkdir -p src/mmCoreAndDevices/DeviceAdapters/DemoCamera/subprojects
	rm -f src/mmCoreAndDevices/DeviceAdapters/DemoCamera/subprojects/MMDevice
	ln -s ../../../MMDevice src/mmCoreAndDevices/DeviceAdapters/DemoCamera/subprojects/MMDevice

	meson setup src/mmCoreAndDevices/DeviceAdapters/DemoCamera/builddir src/mmCoreAndDevices/DeviceAdapters/DemoCamera
	meson compile -C src/mmCoreAndDevices/DeviceAdapters/DemoCamera/builddir
	cp src/mmCoreAndDevices/DeviceAdapters/DemoCamera/builddir/libmmgr_dal_DemoCamera.dylib tests/adapters/darwin/libmmgr_dal_DemoCamera

build-utilities:
	just build-mmdevice
	mkdir -p src/mmCoreAndDevices/DeviceAdapters/Utilities/subprojects
	rm -f src/mmCoreAndDevices/DeviceAdapters/Utilities/subprojects/MMDevice
	ln -s ../../../MMDevice src/mmCoreAndDevices/DeviceAdapters/Utilities/subprojects/MMDevice

	meson setup src/mmCoreAndDevices/DeviceAdapters/Utilities/builddir src/mmCoreAndDevices/DeviceAdapters/Utilities
	meson compile -C src/mmCoreAndDevices/DeviceAdapters/Utilities/builddir
	cp src/mmCoreAndDevices/DeviceAdapters/Utilities/builddir/libmmgr_dal_Utilities.dylib tests/adapters/darwin/libmmgr_dal_Utilities

build-sequencetester:
	just build-mmdevice
	mkdir -p src/mmCoreAndDevices/DeviceAdapters/SequenceTester/subprojects
	rm -f src/mmCoreAndDevices/DeviceAdapters/SequenceTester/subprojects/MMDevice
	ln -s ../../../MMDevice src/mmCoreAndDevices/DeviceAdapters/SequenceTester/subprojects/MMDevice

	meson setup src/mmCoreAndDevices/DeviceAdapters/SequenceTester/builddir src/mmCoreAndDevices/DeviceAdapters/SequenceTester
	meson compile -C src/mmCoreAndDevices/DeviceAdapters/SequenceTester/builddir
	cp src/mmCoreAndDevices/DeviceAdapters/SequenceTester/builddir/libmmgr_dal_SequenceTester.dylib tests/adapters/darwin/libmmgr_dal_SequenceTester
	cp src/mmCoreAndDevices/DeviceAdapters/SequenceTester/builddir/libmmgr_dal_SequenceTester.dylib tests/adapters/darwin/libmmgr_dal_SequenceTester