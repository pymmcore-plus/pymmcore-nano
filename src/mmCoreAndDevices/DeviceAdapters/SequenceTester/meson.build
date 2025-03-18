mmdevice_dep = dependency('mmdevice_dep')
msgpack_dep = dependency('msgpack-cxx', fallback: ['msgpack-cxx', 'msgpack_cxx_dep'])
boost_dep = dependency('boost', modules: ['thread', 'system'], fallback: ['boost', 'boost_dep'], include_type: 'system')

library(
    'mmgr_dal_SequenceTester',
    sources: [
        'InterDevice.cpp',
        'LoggedSetting.cpp',
        'SequenceTester.cpp',
        'SettingLogger.cpp',
        'TextImage.cpp',
        'TriggerInput.cpp',
    ],
    dependencies: [mmdevice_dep, msgpack_dep, boost_dep],
    cpp_args: [
        '-Wno-unused-but-set-variable',
        '-Wno-reorder',
        '-Wno-unused-private-field',
    ],
)

