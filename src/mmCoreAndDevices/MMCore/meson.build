mmdevice_dep = dependency('mmdevice_dep')

mmcore_sources = files(
    'CircularBuffer.cpp',
    'Configuration.cpp',
    'CoreCallback.cpp',
    'CoreFeatures.cpp',
    'CoreProperty.cpp',
    'DeviceManager.cpp',
    'Devices/AutoFocusInstance.cpp',
    'Devices/CameraInstance.cpp',
    'Devices/DeviceInstance.cpp',
    'Devices/GalvoInstance.cpp',
    'Devices/HubInstance.cpp',
    'Devices/ImageProcessorInstance.cpp',
    'Devices/MagnifierInstance.cpp',
    'Devices/SerialInstance.cpp',
    'Devices/ShutterInstance.cpp',
    'Devices/SignalIOInstance.cpp',
    'Devices/SLMInstance.cpp',
    'Devices/StageInstance.cpp',
    'Devices/StateInstance.cpp',
    'Devices/XYStageInstance.cpp',
    'Devices/PressurePumpInstance.cpp',
    'Devices/VolumetricPumpInstance.cpp',
    'Error.cpp',
    'FrameBuffer.cpp',
    'LibraryInfo/LibraryPathsUnix.cpp',
    'LibraryInfo/LibraryPathsWindows.cpp',
    'LoadableModules/LoadedDeviceAdapter.cpp',
    'LoadableModules/LoadedModule.cpp',
    'LoadableModules/LoadedModuleImpl.cpp',
    'LoadableModules/LoadedDeviceAdapterImplMock.cpp',
    'LoadableModules/LoadedDeviceAdapterImplRegular.cpp',
    'LoadableModules/LoadedModuleImplUnix.cpp',
    'LoadableModules/LoadedModuleImplWindows.cpp',
    'Logging/Metadata.cpp',
    'LogManager.cpp',
    'MMCore.cpp',
    'PluginManager.cpp',
    'Semaphore.cpp',
    'Task.cpp',
    'TaskSet.cpp',
    'TaskSet_CopyMemory.cpp',
    'ThreadPool.cpp',
)

mmcore_include_dir = include_directories('.')

cpp_args = [
        '-D_CRT_SECURE_NO_WARNINGS',
        '-DMMDEVICE_CLIENT_BUILD',
]
if host_machine.system() == 'windows'
    cpp_args += '-DNOMINMAX'
endif

# TODO Allow MMCore to be built as a shared library, too. For that, we'd need
# to define the exported symbols on Windows (__declspec(dllexport)).
mmcore_lib = static_library(
    'MMCore',
    sources: mmcore_sources,
    include_directories: mmcore_include_dir,
    dependencies: [
        mmdevice_dep,
        dependency('threads'),
    ],
    cpp_args: cpp_args,
)


mmcore_dep = declare_dependency(
    include_directories: mmcore_include_dir,
    link_with: mmcore_lib,
    dependencies: mmdevice_dep,
)
meson.override_dependency('mmcore_dep', mmcore_dep)


