project(
    'pymmcore-nano',
    'cpp',
    version: '0.0.1',
    meson_version: '>= 1.6.0',
    default_options: ['cpp_std=c++17'],
)
py = import('python').find_installation()
nanobind_dep = dependency('nanobind', static: true)

# ---------- dynamically gather sources and include dirs ----------

print_include_dirs = '''
import pathlib
m = pathlib.Path('src/mmCoreAndDevices')
headers = (*(m/'MMDevice').rglob('*.h'), *(m/'MMCore').rglob('*.h'))
print(';'.join({str(x.parent) for x in headers}))
'''
include_dirs_list = run_command(py.full_path(), '-c', print_include_dirs, check: true).stdout().strip().split(';')
include_dirs = include_directories(include_dirs_list, is_system: true)
foreach dir : include_dirs_list
    message('Include dir: ' + dir)
endforeach

print_sources = '''
import pathlib
m = pathlib.Path('src/mmCoreAndDevices')
sources = (*(m/'MMDevice').rglob('*.cpp'), *(m/'MMCore').rglob('*.cpp'))
print(';'.join({str(x) for x in sources if 'unittest' not in str(x)}))
'''
cpp_sources = run_command(py.full_path(), '-c', print_sources, check: true).stdout().strip().split(';')

foreach src : cpp_sources
    message('Including source: ' + src)
endforeach

# ---------- patch c++14 to c++17 ----------

run_command(py.full_path(), 'scripts/patch_c14_c17.py', check: true)

# --------------------------

cpp_args = ['-DMMDEVICE_CLIENT_BUILD']

if host_machine.system() == 'windows'
    cpp_args += ['-DNOMINMAX', '-D_CRT_SECURE_NO_WARNINGS']
endif

ext_module = py.extension_module(
    '_pymmcore_nano',
    sources: ['src/_pymmcore_nano.cc'] + cpp_sources,
    dependencies: [nanobind_dep],
    include_directories: include_dirs,
    install: true,
    cpp_args: cpp_args,
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
        meson.project_source_root() + '/src/_pymmcore_nano.pyi',
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
    'src/_pymmcore_nano.pyi',
    install_dir: py.get_install_dir(),
)

test(
    'test_script',
    py,
    args: ['-m', 'pytest', '--color=yes', '-v'],
    workdir: meson.current_source_dir(),
)