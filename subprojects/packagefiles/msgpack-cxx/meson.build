project('msgpack-cxx', 'cpp', version: '7.0.0')

msgpack_dep = declare_dependency(
  include_directories : include_directories('include')
)

meson.override_dependency('msgpack-cxx', msgpack_dep)
