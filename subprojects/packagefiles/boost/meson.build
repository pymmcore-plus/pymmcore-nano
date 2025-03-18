project('boost', 'cpp', version: '1.83.0', license: 'Boost')

# Use relative path for include directories.
boost_inc = include_directories('.')

# --- Build Boost.System ---
boost_system_lib = static_library(
  'boost_system',
  files(
    'libs/system/src/error_code.cpp'
  ),
  include_directories: boost_inc,
)

# --- Build Boost.Thread ---

boost_thread_lib = static_library(
  'boost_thread',
  files(
    'libs/thread/src/pthread/thread.cpp',
    'libs/thread/src/pthread/once.cpp',
    'libs/thread/src/future.cpp'
  ),
  include_directories: boost_inc,
  dependencies: dependency('threads', required: true),
)

# Declare dependency with both libraries.
boost_dep = declare_dependency(
  include_directories: boost_inc,
  link_with: [boost_system_lib, boost_thread_lib]
)

meson.override_dependency('boost', boost_dep)
