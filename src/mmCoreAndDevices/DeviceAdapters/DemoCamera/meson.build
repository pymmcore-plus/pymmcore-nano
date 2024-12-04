# This Meson script is experimental and potentially incomplete. It is not part
# of the supported build system for Micro-Manager or mmCoreAndDevices.

project(
    'DemoCamera',
    'cpp',
    meson_version: '>=1.2.0',
    default_options: [
        'cpp_std=c++14',
        'warning_level=3',
    ],
)

# MMDevice must be copied into subprojects/ for this experimental build to work
# (unless MMCore is itself being used as a subproject).
mmdevice_proj = subproject('MMDevice')
mmdevice_dep = mmdevice_proj.get_variable('mmdevice')

# Define the target (shared library)
library(
    'mmgr_dal_DemoCamera',
    ['DemoCamera.cpp'],
    dependencies: [mmdevice_dep],
    cpp_args: [
        '-Wno-unused-but-set-variable',
        '-Wno-reorder',
        '-Wno-unused-private-field',
    ],
)