# replace the version by running:
# meson rewrite kwargs set project / version $(python scripts/extract_version.py)
project(
  'pymmcore-nano',
  'cpp',
version : '11.10.0.74.0',
  meson_version : '>=1.4.0',
  default_options : ['cpp_std=c++17', 'warning_level=3']
)if get_option('hold_gil')
    cpp_args += ['-DHOLD_GIL']
endif
if get_option('match_swig')
    cpp_args += ['-DMATCH_SWIG']
endif

ext_module = py.extension_module(
    '_pymmcore_nano',
    sources: ['src/_pymmcore_nano.cc'],
    dependencies: [nanobind_dep, mmcore_dep],
    install: true,
    subdir: 'pymmcore_nano',
    cpp_args: cpp_args + ['-DNB_DOMAIN=pmn'],
)

# Create stubs using nanobind.stubgen
custom_target(
    'generate_stubs',
    build_by_default: true,
    input: [ext_module],
    output: '_pymmcore_nano.pyi',
    command: [
        py.full_path(),
        meson.project_source_root() + '/scripts/build_stubs.py',
        ext_module.full_path(),
        meson.project_source_root()
        + '/src/pymmcore_nano/_pymmcore_nano.pyi',
    ],
    depends: ext_module,
)

# install the Python package into the site-packages directory
install_subdir(
    'src/pymmcore_nano',
    install_dir: py.get_install_dir() / 'pymmcore_nano',
    strip_directory: true,
)

# also install the stubs into the site-packages directory
install_data(
    'src/pymmcore_nano/_pymmcore_nano.pyi',
    install_dir: py.get_install_dir() / 'pymmcore_nano',
)

test(
    'test_script',
    py,
    args: ['-m', 'pytest', '--color=yes', '-v'],
    workdir: meson.current_source_dir(),
)

meson.add_dist_script(py.full_path(), meson.current_source_dir() / 'scripts/generate_dist.py')
