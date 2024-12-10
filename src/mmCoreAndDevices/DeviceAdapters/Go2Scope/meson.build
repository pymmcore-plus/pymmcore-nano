# This Meson script is experimental and potentially incomplete. It is not part
# of the supported build system for Micro-Manager or mmCoreAndDevices.

project(
    'Go2Scope',
    'cpp',
    meson_version: '>=1.2.0',
    default_options: [
        'cpp_std=c++17',
        'warning_level=3',
    ],
)

boost_dep = dependency('boost', modules : ['filesystem', 'system'])
aquire_zarr_dep = dependency('acquire-zarr')
curl_dep = dependency('libcurl', required: true)
libacquire_logger_path = meson.current_source_dir() + '/libacquire_logger.a'

# MMDevice must be copied into subprojects/ for this experimental build to work
# (unless MMCore is itself being used as a subproject).
mmdevice_proj = subproject('MMDevice')
mmdevice_dep = mmdevice_proj.get_variable('mmdevice')

g2s_sources = files(
    'AcqZarrStorage.cpp',
    'CFileUtil.cpp',
    # 'G2SBigTiffDataset.cpp',
    # 'G2SBigTiffStorage.cpp',
    # 'G2SBigTiffStream.cpp',
    'G2SStorage.cpp',
)

# Define the target (shared library)
library(
    'mmgr_dal_Go2Scope',
    sources: g2s_sources,
    dependencies: [mmdevice_dep, boost_dep, aquire_zarr_dep, curl_dep],
    link_args: [libacquire_logger_path],  # Add the copied logger library
    cpp_args: [
        '-Wno-unused-parameter',
    ],
)