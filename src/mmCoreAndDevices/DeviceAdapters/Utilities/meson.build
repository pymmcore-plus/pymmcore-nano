mmdevice_dep = dependency('mmdevice_dep')

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
    dependencies: [mmdevice_dep],
)