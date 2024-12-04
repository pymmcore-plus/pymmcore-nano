# replace the version by running:
# meson rewrite kwargs set project / version $(python scripts/extract_version.py)
project(
  'pymmcore-nano',
  'cpp',
version : '11.2.1.71.0.dev1',
  meson_version : '>= 1.2.0',
  default_options : ['cpp_std=c++17']
)
py = import('python').find_installation()
nanobind_dep = dependency('nanobind', static: true)

# Run a command to get the Python include path
python_include_path = run_command(
    py.full_path(), ['-c', 'import sysconfig; print(sysconfig.get_paths()["include"])']
).stdout().strip()

# Include directories
include_dirs = include_directories(
    'src/mmCoreAndDevices/MMCore',
    'src/mmCoreAndDevices/MMCore/Devices',
    'src/mmCoreAndDevices/MMCore/LibraryInfo',
    'src/mmCoreAndDevices/MMCore/LoadableModules',
    'src/mmCoreAndDevices/MMCore/Logging',
    'src/mmCoreAndDevices/MMDevice',
    python_include_path,
)

mmcore_sources = files(
    'src/mmCoreAndDevices/MMCore/CircularBuffer.cpp',
    'src/mmCoreAndDevices/MMCore/Configuration.cpp',
    'src/mmCoreAndDevices/MMCore/CoreCallback.cpp',
    'src/mmCoreAndDevices/MMCore/CoreFeatures.cpp',
    'src/mmCoreAndDevices/MMCore/CoreProperty.cpp',
    'src/mmCoreAndDevices/MMCore/DeviceManager.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/AutoFocusInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/CameraInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/DeviceInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/GalvoInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/HubInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/ImageProcessorInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/MagnifierInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/SerialInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/ShutterInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/SignalIOInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/SLMInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/StageInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/StateInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Devices/XYStageInstance.cpp',
    'src/mmCoreAndDevices/MMCore/Error.cpp',
    'src/mmCoreAndDevices/MMCore/FrameBuffer.cpp',
    'src/mmCoreAndDevices/MMCore/LibraryInfo/LibraryPathsUnix.cpp',
    'src/mmCoreAndDevices/MMCore/LibraryInfo/LibraryPathsWindows.cpp',
    'src/mmCoreAndDevices/MMCore/LoadableModules/LoadedDeviceAdapter.cpp',
    'src/mmCoreAndDevices/MMCore/LoadableModules/LoadedModule.cpp',
    'src/mmCoreAndDevices/MMCore/LoadableModules/LoadedModuleImpl.cpp',
    'src/mmCoreAndDevices/MMCore/LoadableModules/LoadedModuleImplUnix.cpp',
    'src/mmCoreAndDevices/MMCore/LoadableModules/LoadedModuleImplWindows.cpp',
    'src/mmCoreAndDevices/MMCore/Logging/Metadata.cpp',
    'src/mmCoreAndDevices/MMCore/LogManager.cpp',
    'src/mmCoreAndDevices/MMCore/MMCore.cpp',
    'src/mmCoreAndDevices/MMCore/PluginManager.cpp',
    'src/mmCoreAndDevices/MMCore/Semaphore.cpp',
    'src/mmCoreAndDevices/MMCore/Task.cpp',
    'src/mmCoreAndDevices/MMCore/TaskSet_CopyMemory.cpp',
    'src/mmCoreAndDevices/MMCore/TaskSet.cpp',
    'src/mmCoreAndDevices/MMCore/ThreadPool.cpp',
    'src/mmCoreAndDevices/MMDevice/Debayer.cpp',
    'src/mmCoreAndDevices/MMDevice/DeviceUtils.cpp',
    'src/mmCoreAndDevices/MMDevice/ImgBuffer.cpp',
    'src/mmCoreAndDevices/MMDevice/MMDevice.cpp',
    'src/mmCoreAndDevices/MMDevice/ModuleInterface.cpp',
    'src/mmCoreAndDevices/MMDevice/Property.cpp',
)

# ---------- patch c++14 to c++17 ----------

run_command(py.full_path(), 'scripts/patch_sources.py', check: true)

# --------------------------

cpp_args = ['-DMMDEVICE_CLIENT_BUILD', '-DMATCH_SWIG']

if host_machine.system() == 'windows'
    cpp_args += ['-DNOMINMAX', '-D_CRT_SECURE_NO_WARNINGS']
endif

ext_module = py.extension_module(
    '_pymmcore_nano',
    sources: ['src/_pymmcore_nano.cc'] + mmcore_sources,
    dependencies: [nanobind_dep],
    include_directories: include_dirs,
    install: true,
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

meson.add_dist_script(py.full_path(), meson.current_source_dir() / 'scripts/generate_dist.py')
