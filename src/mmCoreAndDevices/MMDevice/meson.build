cpp_args = []
if get_option('client_interface')
    cpp_args += '-DMMDEVICE_CLIENT_BUILD'
endif

# We intentionally do NOT define NOMINMAX on Windows. MMDevice should compile
# correctly with or without Windows.h's min()/max() macros.

mmdevice_sources = files(
    'Debayer.cpp',
    'DeviceUtils.cpp',
    'ImgBuffer.cpp',
    'MMDevice.cpp',
    'ModuleInterface.cpp',
    'Property.cpp',
)

mmdevice_include_dir = include_directories('.')
mmdevice_lib = static_library(
    'MMDevice',
    sources: mmdevice_sources,
    include_directories: mmdevice_include_dir,
    cpp_args: cpp_args,
    dependencies: [dependency('threads')],
)

mmdevice_dep = declare_dependency(
    compile_args: cpp_args,
    include_directories: mmdevice_include_dir,
    link_with: mmdevice_lib,
)
meson.override_dependency('mmdevice_dep', mmdevice_dep)

# For providing include dir to SWIG when using this project as a subproject
swig_include_dirs = [meson.current_source_dir()]
