# This Meson script is experimental and potentially incomplete. It is not part
# of the supported build system for Micro-Manager or mmCoreAndDevices.

project(
    'Utilities',
    'cpp',
    meson_version: '>=1.2.0',
    default_options: [
        'cpp_std=c++14',
        'warning_level=3',
    ],
)

boost_dep = dependency('boost')

# MMDevice must be copied into subprojects/ for this experimental build to work
# (unless MMCore is itself being used as a subproject).
mmdevice_proj = subproject('MMDevice')
mmdevice_dep = mmdevice_proj.get_variable('mmdevice')

util_sources = files(
    'AutoFocusStage.cpp',
    'ComboXYStage.cpp',
    'DAGalvo.cpp',
    'DAMonochromator.cpp',
    'DAShutter.cpp',
    'DATTLStateDevice.cpp',
    'DAXYStage.cpp',
    'DAZStage.cpp',
    'MultiCamera.cpp',
    'MultiDAStateDevice.cpp',
    'MultiShutter.cpp',
    'MultiStage.cpp',
    'SerialDTRShutter.cpp',
    'SingleAxisStage.cpp',
    'StateDeviceShutter.cpp',
    'Utilities.cpp',
)

# Define the target (shared library)
library(
    'mmgr_dal_Utilities',
    sources: util_sources,
    dependencies: [mmdevice_dep, boost_dep],
)