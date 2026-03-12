// Custom type caster: std::vector<T> <-> Python tuple (instead of list).
// from_python accepts any sequence (same as nanobind's list_caster).
// from_cpp produces a tuple (unlike nanobind's list_caster which produces a list).

#pragma once

#include <vector>

#include <nanobind/nanobind.h>

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <typename List, typename Entry> struct tuple_seq_caster {
    NB_TYPE_CASTER(List, io_name(NB_TYPING_SEQUENCE "[", NB_TYPING_TUPLE "[") +
                             make_caster<Entry>::Name + io_name("]", ", ...]"))

    using Caster = make_caster<Entry>;

    template <typename T> using has_reserve = decltype(std::declval<T>().reserve(0));

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept {
        size_t size;
        PyObject *temp;
        PyObject **o = seq_get(src.ptr(), &size, &temp);

        value.clear();

        if constexpr (is_detected_v<has_reserve, List>)
            value.reserve(size);

        Caster caster;
        bool success = o != nullptr;

        flags = flags_for_local_caster<Entry>(flags);

        for (size_t i = 0; i < size; ++i) {
            if (!caster.from_python(o[i], flags, cleanup) ||
                !caster.template can_cast<Entry>()) {
                success = false;
                break;
            }
            value.push_back(caster.operator cast_t<Entry>());
        }

        Py_XDECREF(temp);
        return success;
    }

    template <typename T>
    static handle from_cpp(T &&src, rv_policy policy, cleanup_list *cleanup) {
        object ret = steal(PyTuple_New(src.size()));

        if (ret.is_valid()) {
            Py_ssize_t index = 0;

            for (auto &&value : src) {
                handle h = Caster::from_cpp(forward_like_<T>(value), policy, cleanup);

                if (!h.is_valid()) {
                    ret.reset();
                    break;
                }

                PyTuple_SET_ITEM(ret.ptr(), index++, h.ptr());
            }
        }

        return ret.release();
    }
};

template <typename Type, typename Alloc>
struct type_caster<std::vector<Type, Alloc>>
    : tuple_seq_caster<std::vector<Type, Alloc>, Type> {};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
