mmdevice_dep = dependency('mmdevice_dep')
msgpack_dep = dependency('msgpack-cxx', fallback: ['msgpack-cxx', 'msgpack_cxx_dep'])
boost_dep = dependency('boost', modules: ['thread', 'system'], fallback: ['boost', 'boost_dep'], include_type: 'system')

cpp_args = []
if host_machine.system() == 'windows'
    cpp_args += [
        '/wd4101',  # equivalent to -Wno-unused-but-set-variable
        '/wd5038',  # equivalent to -Wno-reorder
        '/wd4624',  # equivalent to -Wno-unused-private-field
    ]
else
    cpp_args += [
        '-Wno-unused-but-set-variable',
        '-Wno-reorder',
        '-Wno-unused-private-field',
    ]
endif

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
    cpp_args: cpp_args,
)

