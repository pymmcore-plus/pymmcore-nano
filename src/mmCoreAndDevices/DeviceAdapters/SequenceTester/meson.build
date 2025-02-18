# This Meson script is experimental and potentially incomplete. It is not part
# of the supported build system for Micro-Manager or mmCoreAndDevices.

project(
    'SequenceTester',
    'cpp',
    meson_version: '>=1.2.0',
    default_options: [
        'cpp_std=c++14',
        'warning_level=3',
    ],
)

msgpack_cxx_dep = dependency('msgpack-cxx')
boost_dep = dependency('boost', modules: ['thread', 'system'], include_type: 'system')

# MMDevice must be copied into subprojects/ for this experimental build to work
# (unless MMCore is itself being used as a subproject).
mmdevice_proj = subproject('MMDevice')
mmdevice_dep = mmdevice_proj.get_variable('mmdevice')

seqtester_sources = files(
    'InterDevice.cpp',
    'LoggedSetting.cpp',
    'SequenceTester.cpp',
    'SettingLogger.cpp',
    'TextImage.cpp',
    'TriggerInput.cpp',
)

# Define the target (shared library)
library(
    'mmgr_dal_SequenceTester',
    sources: seqtester_sources,
    dependencies: [mmdevice_dep, msgpack_cxx_dep, boost_dep],
    cpp_args: [
        '-Wno-unused-but-set-variable',
        '-Wno-reorder',
        '-Wno-unused-private-field',
    ],
)