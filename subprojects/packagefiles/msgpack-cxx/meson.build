project('msgpack-cxx', 'cpp', version: '7.0.0')
boost_dep = dependency('boost', include_type: 'system')

msgpack_dep = declare_dependency(
  include_directories : include_directories('include'),
  dependencies : [boost_dep]
)

meson.override_dependency('msgpack-cxx', msgpack_dep)
