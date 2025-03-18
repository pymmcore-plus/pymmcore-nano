mmdevice_dep = dependency('mmdevice_dep')


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


if host_machine.system() == 'windows'
    cpp_args += ['-DNOMINMAX']
endif

library(
    'mmgr_dal_DemoCamera',
    ['DemoCamera.cpp'],
    dependencies: [mmdevice_dep],
    cpp_args: cpp_args,
)