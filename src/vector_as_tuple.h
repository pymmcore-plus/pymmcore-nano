/*
    Type caster that returns std::vector<T> to Python as a tuple (as pymmcore/SWIG
    does) instead of nanobind's default list.  Include this instead of
    <nanobind/stl/vector.h>.

    Only the C++ -> Python direction differs from nanobind's list_caster: arguments
    still accept any sequence.
*/

#pragma once

#include <nanobind/stl/detail/nb_list.h>
#include <vector>

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <typename Type, typename Alloc>
struct type_caster<std::vector<Type, Alloc>> : list_caster<std::vector<Type, Alloc>, Type> {
    // literal names, like nanobind's own list_caster (the NB_TYPING_* macros
    // were removed in nanobind 3)
    static constexpr auto Name = io_name("collections.abc.Sequence", "tuple") +
                                 const_name("[") + make_caster<Type>::Name +
                                 io_name("]", ", ...]");

    // same as list_caster::from_cpp, but building a tuple
    template <typename T>
    static handle from_cpp(T &&src, rv_policy policy, cleanup_list *cleanup) {
        object ret = steal(PyTuple_New((Py_ssize_t) src.size()));

        if (ret.is_valid()) {
            Py_ssize_t index = 0;

            for (auto &&value : src) {
                handle h =
                    make_caster<Type>::from_cpp(forward_like_<T>(value), policy, cleanup);

                if (!h.is_valid()) {
                    ret.reset();
                    break;
                }

                NB_TUPLE_SET_ITEM(ret.ptr(), index++, h.ptr());
            }
        }

        return ret.release();
    }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
