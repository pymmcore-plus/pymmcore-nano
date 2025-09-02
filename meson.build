# replace the version by running:
# meson rewrite kwargs set project / version $(python scripts/extract_version.py)
project(
    'pymmcore-nano',
    'cpp',
    version: '11.10.0.74.0',
    meson_version: '>=1.4.0',
    default_options: ['cpp_std=c++17'],
)

if host_machine.system() == 'darwin'
    add_project_arguments('-U_LIBCPP_ENABLE_ASSERTIONS', language: 'cpp')
endif

py = import('python').find_installation(pure: false)
nanobind_dep = dependency('nanobind', static: true)

# Run a command to get the Python include path
python_include_path = run_command(
    py.full_path(),
    ['-c', 'import sysconfig; print(sysconfig.get_paths()["include"])'],
).stdout().strip()

mmcore_proj = subproject(
    'mmcore',
    default_options: {'default_library': 'static', 'tests': 'disabled'},
)
mmcore_dep = mmcore_proj.get_variable('mmcore')

# --------------------------

cpp_args = ['-DMMDEVICE_CLIENT_BUILD']

if host_machine.system() == 'windows'
    cpp_args += ['-DNOMINMAX', '-D_CRT_SECURE_NO_WARNINGS']
endif

if get_option('hold_gil')
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
stub_target = custom_target(
    'generate_stubs',
    input: [ext_module],
    output: '_pymmcore_nano.pyi',
    command: [
        py.full_path(),
        meson.project_source_root() / 'scripts' / 'build_stubs.py',
        '@INPUT@', # path to built extension
        '@OUTPUT@', # write stub to this path
    ],
    build_by_default: true,
    install: true,
    install_dir: py.get_install_dir() / 'pymmcore_nano',
    depends: ext_module,
)

# Copy stub to source tree for development (so Pyright can find it)
custom_target(
    'copy_stubs_to_src',
    input: stub_target,
    output: 'stub_copied_marker',
    command: [
        py.full_path(),
        '-c',
        'import shutil; shutil.copy(r"@INPUT@", r"@0@")'.format(
            meson.project_source_root() / 'src' / 'pymmcore_nano' / '_pymmcore_nano.pyi'
        )
    ],
    build_by_default: true,
    depends: stub_target,
)

# Install the pure-Python package bits
py.install_sources(
    files(
        'src/pymmcore_nano/__init__.py',
        'src/pymmcore_nano/py.typed',
    ),
    subdir: 'pymmcore_nano',
)

test(
    'test_script',
    py,
    args: ['-m', 'pytest', '--color=yes', '-v'],
    workdir: meson.current_source_dir(),
)