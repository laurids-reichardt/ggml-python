"""This module is the core of the ggml-python library, it exposes a low-level [ctypes](https://docs.python.org/3/library/ctypes.html)-based interface for ggml.

Structures and functions in the `ggml.ggml` module map directly to the original ggml C library and
they operate at a fairly low level.
No additional runtime checks checks are performed nor is memory management handled automatically.
You've been warned :).

With that in mind here are some useful things to keep in mind

- Functions accept both ctypes types (c_int, c_bool, c_float, etc.) and Python types (int, bool, float, etc.) as parameters.
- Functions return Python types for simple values (int, bool, float, etc.) and ctypes types for complex values ([ggml_context_p][ggml.ggml_context_p], [ggml_tensor_p][ggml.ggml_tensor_p], etc.).
- Memory management is the responsibility of the user. The user must call [ggml.ggml_free][] on the context after calling [ggml.ggml_init][].

Example

```python
import ggml
import ctypes

# Allocate a new context with 16 MB of memory
params = ggml.ggml_init_params(mem_size=16 * 1024 * 1024, mem_buffer=None)
ctx = ggml.ggml_init(params=params)

# Instantiate tensors
x = ggml.ggml_new_tensor_1d(ctx, ggml.GGML_TYPE_F32, 1)
a = ggml.ggml_new_tensor_1d(ctx, ggml.GGML_TYPE_F32, 1)
b = ggml.ggml_new_tensor_1d(ctx, ggml.GGML_TYPE_F32, 1)

# Use ggml operations to build a computational graph
x2 = ggml.ggml_mul(ctx, x, x)
f = ggml.ggml_add(ctx, ggml.ggml_mul(ctx, a, x2), b)

gf = ggml.ggml_build_forward(f)

# Set the input values
ggml.ggml_set_f32(x, 2.0)
ggml.ggml_set_f32(a, 3.0)
ggml.ggml_set_f32(b, 4.0)

# Compute the graph
ggml.ggml_graph_compute(ctx, ctypes.pointer(gf))

# Get the output value
output = ggml.ggml_get_f32_1d(f, 0)
assert output == 16.0

# Free the context
ggml.ggml_free(ctx)
```

"""
import os
import sys
import ctypes
import pathlib
import importlib.resources
from typing import List, Optional, Sequence, Union
from typing_extensions import TypeAlias


# Load the library
def load_shared_library(module_name: str, lib_base_name: str):
    # Construct the paths to the possible shared library names
    base_path = pathlib.Path(__file__).parent.resolve()
    # Searching for the library in the current directory under the name "libggml" (default name
    # for ggml) and "ggml" (default name for this repo)
    lib_names: List[str] = [
        f"lib{lib_base_name}.so",
        f"lib{lib_base_name}.dylib",
        f"{lib_base_name}.dll",
    ]

    path: Optional[pathlib.Path] = None

    for lib_name in lib_names:
        try:
            with importlib.resources.path(module_name, lib_name) as p:
                if os.path.exists(p):
                    path = p
                    break
        except FileNotFoundError:
            pass

    if path is None:
        raise FileNotFoundError(
            f"Shared library with base name '{lib_base_name}' not found"
        )

    cdll_args = dict()  # type: ignore
    # Add the library directory to the DLL search path on Windows (if needed)
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        os.add_dll_directory(str(base_path))
        cdll_args["winmode"] = 0

    # Try to load the shared library, handling potential errors
    try:
        return ctypes.CDLL(str(path), **cdll_args)
    except Exception as e:
        raise RuntimeError(f"Failed to load shared library '{path}': {e}")


module_name = "ggml"
lib_base_name = "ggml"
lib = load_shared_library(module_name, lib_base_name)


#####################################################
# GGML API
# source: ggml.h
#####################################################


# #define GGML_FILE_MAGIC   0x67676d6c // "ggml"
GGML_FILE_MAGIC = int("0x67676d6c", 16)
# #define GGML_FILE_VERSION 1
GGML_FILE_VERSION = 1
# #define GGML_QNT_VERSION        2    // bump this on quantization format changes
GGML_QNT_VERSION = 2
# #define GGML_QNT_VERSION_FACTOR 1000 // do not change this
GGML_QNT_VERSION_FACTOR = 1000
# #define GGML_MAX_DIMS          4
GGML_MAX_DIMS = 4
# #define GGML_MAX_NODES         4096
GGML_MAX_NODES = 4096
# #define GGML_MAX_PARAMS        256
GGML_MAX_PARAMS = 256
# #define GGML_MAX_CONTEXTS      64
GGML_MAX_CONTEXTS = 64
# #define GGML_MAX_OPT           4
GGML_MAX_OPT = 4
# #define GGML_MAX_NAME          48
GGML_MAX_NAME = 48
# #define GGML_DEFAULT_N_THREADS 4
GGML_DEFAULT_N_THREADS = 4


# TODO: Check if this is correct
# typedef uint16_t ggml_fp16_t;
ggml_fp16_t = ctypes.c_uint16


# GGML_API float       ggml_fp16_to_fp32(ggml_fp16_t x);
def ggml_fp16_to_fp32(x: ggml_fp16_t) -> float:
    return lib.ggml_fp16_to_fp32(x)


lib.ggml_fp16_to_fp32.argtypes = [ggml_fp16_t]
lib.ggml_fp16_to_fp32.restype = ctypes.c_float


# GGML_API ggml_fp16_t ggml_fp32_to_fp16(float x);
def ggml_fp32_to_fp16(x: ctypes.c_float) -> int:
    return lib.ggml_fp32_to_fp16(x)


lib.ggml_fp32_to_fp16.argtypes = [ctypes.c_float]
lib.ggml_fp32_to_fp16.restype = ggml_fp16_t


# GGML_API void ggml_fp16_to_fp32_row(const ggml_fp16_t * x, float * y, size_t n);
def ggml_fp16_to_fp32_row(
    x,  # type: ctypes.Array[ggml_fp16_t]
    y,  # type: ctypes.Array[ctypes.c_float]
    n: ctypes.c_size_t,
) -> None:
    return lib.ggml_fp16_to_fp32_row(x, y, n)


lib.ggml_fp16_to_fp32_row.argtypes = [
    ctypes.POINTER(ggml_fp16_t),
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_size_t,
]
lib.ggml_fp16_to_fp32_row.restype = None


# GGML_API void ggml_fp32_to_fp16_row(const float * x, ggml_fp16_t * y, size_t n);
def ggml_fp32_to_fp16_row(
    x,  # type: ctypes.Array[ctypes.c_float]
    y,  # type: ctypes.Array[ggml_fp16_t]
    n: ctypes.c_size_t,
) -> None:
    return lib.ggml_fp32_to_fp16_row(x, y, n)


lib.ggml_fp32_to_fp16_row.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ggml_fp16_t),
    ctypes.c_size_t,
]
lib.ggml_fp32_to_fp16_row.restype = None


# struct ggml_context;
ggml_context_p = ctypes.c_void_p
"""Opaque pointer to a ggml_context.

ggml_context structs are not accessed directly instead they must be created using [ggml_init](ggml.ggml_init) and freed using [ggml_free](ggml.ggml_free)."""


# enum ggml_type {
#     GGML_TYPE_F32  = 0,
#     GGML_TYPE_F16  = 1,
#     GGML_TYPE_Q4_0 = 2,
#     GGML_TYPE_Q4_1 = 3,
#     // GGML_TYPE_Q4_2 = 4, support has been removed
#     // GGML_TYPE_Q4_3 (5) support has been removed
#     GGML_TYPE_Q5_0 = 6,
#     GGML_TYPE_Q5_1 = 7,
#     GGML_TYPE_Q8_0 = 8,
#     GGML_TYPE_Q8_1 = 9,
#     GGML_TYPE_Q2_K = 10,
#     GGML_TYPE_Q3_K = 11,
#     GGML_TYPE_Q4_K = 12,
#     GGML_TYPE_Q5_K = 13,
#     GGML_TYPE_Q6_K = 14,
#     GGML_TYPE_Q8_K = 15,
#     GGML_TYPE_I8,
#     GGML_TYPE_I16,
#     GGML_TYPE_I32,
#     GGML_TYPE_COUNT,
# };
GGML_TYPE_F32 = 0
GGML_TYPE_F16 = 1
GGML_TYPE_Q4_0 = 2
GGML_TYPE_Q4_1 = 3
GGML_TYPE_Q5_0 = 6
GGML_TYPE_Q5_1 = 7
GGML_TYPE_Q8_0 = 8
GGML_TYPE_Q8_1 = 9
GGML_TYPE_Q2_K = 10
GGML_TYPE_Q3_K = 11
GGML_TYPE_Q4_K = 12
GGML_TYPE_Q5_K = 13
GGML_TYPE_Q6_K = 14
GGML_TYPE_Q8_K = 15
GGML_TYPE_I8 = 16
GGML_TYPE_I16 = 17
GGML_TYPE_I32 = 18
GGML_TYPE_COUNT = 19


# enum ggml_backend {
#     GGML_BACKEND_CPU = 0,
#     GGML_BACKEND_GPU = 10,
#     GGML_BACKEND_GPU_SPLIT = 20,
# };
GGML_BACKEND_CPU = 0
GGML_BACKEND_GPU = 10
GGML_BACKEND_GPU_SPLIT = 20


# // model file types
# enum ggml_ftype {
#     GGML_FTYPE_UNKNOWN     = -1,
#     GGML_FTYPE_ALL_F32     = 0,
#     GGML_FTYPE_MOSTLY_F16  = 1,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q4_0 = 2,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q4_1 = 3,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q4_1_SOME_F16 = 4, // tok_embeddings.weight and output.weight are F16
#     GGML_FTYPE_MOSTLY_Q8_0 = 7,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q5_0 = 8,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q5_1 = 9,  // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q2_K = 10, // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q3_K = 11, // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q4_K = 12, // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q5_K = 13, // except 1d tensors
#     GGML_FTYPE_MOSTLY_Q6_K = 14, // except 1d tensors
# };
GGML_FTYPE_UNKNOWN = -1
GGML_FTYPE_ALL_F32 = 0
GGML_FTYPE_MOSTLY_F16 = 1
GGML_FTYPE_MOSTLY_Q4_0 = 2
GGML_FTYPE_MOSTLY_Q4_1 = 3
GGML_FTYPE_MOSTLY_Q4_1_SOME_F16 = 4
GGML_FTYPE_MOSTLY_Q8_0 = 7
GGML_FTYPE_MOSTLY_Q5_0 = 8
GGML_FTYPE_MOSTLY_Q5_1 = 9
GGML_FTYPE_MOSTLY_Q2_K = 10
GGML_FTYPE_MOSTLY_Q3_K = 11
GGML_FTYPE_MOSTLY_Q4_K = 12
GGML_FTYPE_MOSTLY_Q5_K = 13
GGML_FTYPE_MOSTLY_Q6_K = 14


# // available tensor operations:
# enum ggml_op {
#     GGML_OP_NONE = 0,

#     GGML_OP_DUP,
#     GGML_OP_ADD,
#     GGML_OP_ADD1,
#     GGML_OP_ACC,
#     GGML_OP_SUB,
#     GGML_OP_MUL,
#     GGML_OP_DIV,
#     GGML_OP_SQR,
#     GGML_OP_SQRT,
#     GGML_OP_LOG,
#     GGML_OP_SUM,
#     GGML_OP_SUM_ROWS,
#     GGML_OP_MEAN,
#     GGML_OP_REPEAT,
#     GGML_OP_REPEAT_BACK,
#     GGML_OP_ABS,
#     GGML_OP_SGN,
#     GGML_OP_NEG,
#     GGML_OP_STEP,
#     GGML_OP_RELU,
#     GGML_OP_GELU,
#     GGML_OP_GELU_QUICK,
#     GGML_OP_SILU,
#     GGML_OP_SILU_BACK,
#     GGML_OP_NORM, // normalize
#     GGML_OP_RMS_NORM,
#     GGML_OP_RMS_NORM_BACK,

#     GGML_OP_MUL_MAT,
#     GGML_OP_OUT_PROD,

#     GGML_OP_SCALE,
#     GGML_OP_SET,
#     GGML_OP_CPY,
#     GGML_OP_CONT,
#     GGML_OP_RESHAPE,
#     GGML_OP_VIEW,
#     GGML_OP_PERMUTE,
#     GGML_OP_TRANSPOSE,
#     GGML_OP_GET_ROWS,
#     GGML_OP_GET_ROWS_BACK,
#     GGML_OP_DIAG,
#     GGML_OP_DIAG_MASK_INF,
#     GGML_OP_DIAG_MASK_ZERO,
#     GGML_OP_SOFT_MAX,
#     GGML_OP_SOFT_MAX_BACK,
#     GGML_OP_ROPE,
#     GGML_OP_ROPE_BACK,
#     GGML_OP_ALIBI,
#     GGML_OP_CLAMP,
#     GGML_OP_CONV_1D_1S_PH,
#     GGML_OP_CONV_1D_2S_PH,
#     GGML_OP_CONV_2D_SK_P0,

#     GGML_OP_FLASH_ATTN,
#     GGML_OP_FLASH_FF,
#     GGML_OP_FLASH_ATTN_BACK,
#     GGML_OP_WIN_PART,
#     GGML_OP_WIN_UNPART,

#     GGML_OP_MAP_UNARY,
#     GGML_OP_MAP_BINARY,

#     GGML_OP_MAP_CUSTOM1,
#     GGML_OP_MAP_CUSTOM2,
#     GGML_OP_MAP_CUSTOM3,

#     GGML_OP_CROSS_ENTROPY_LOSS,
#     GGML_OP_CROSS_ENTROPY_LOSS_BACK,

#     GGML_OP_COUNT,
# };
GGML_OP_NONE = 0
GGML_OP_DUP = 1
GGML_OP_ADD = 2
GGML_OP_ADD1 = 3
GGML_OP_ACC = 4
GGML_OP_SUB = 5
GGML_OP_MUL = 6
GGML_OP_DIV = 7
GGML_OP_SQR = 8
GGML_OP_SQRT = 9
GGML_OP_LOG = 10
GGML_OP_SUM = 11
GGML_OP_SUM_ROWS = 12
GGML_OP_MEAN = 13
GGML_OP_REPEAT = 14
GGML_OP_REPEAT_BACK = 15
GGML_OP_ABS = 16
GGML_OP_SGN = 17
GGML_OP_NEG = 18
GGML_OP_STEP = 19
GGML_OP_RELU = 20
GGML_OP_GELU = 21   
GGML_OP_GELU_QUICK = 22
GGML_OP_SILU = 23
GGML_OP_SILU_BACK = 24
GGML_OP_NORM = 25
GGML_OP_RMS_NORM = 26
GGML_OP_RMS_NORM_BACK = 27
GGML_OP_MUL_MAT = 28
GGML_OP_OUT_PROD = 29
GGML_OP_SCALE = 30
GGML_OP_SET = 31
GGML_OP_CPY = 32
GGML_OP_CONT = 33
GGML_OP_RESHAPE = 34
GGML_OP_VIEW = 35
GGML_OP_PERMUTE = 36
GGML_OP_TRANSPOSE = 37
GGML_OP_GET_ROWS = 38
GGML_OP_GET_ROWS_BACK = 39
GGML_OP_DIAG = 40
GGML_OP_DIAG_MASK_INF = 41
GGML_OP_DIAG_MASK_ZERO = 42
GGML_OP_SOFT_MAX = 43
GGML_OP_SOFT_MAX_BACK = 44
GGML_OP_ROPE = 45
GGML_OP_ROPE_BACK = 46
GGML_OP_ALIBI = 47
GGML_OP_CLAMP = 48
GGML_OP_CONV_1D_1S_PH = 49
GGML_OP_CONV_1D_2S_PH = 50
GGML_OP_CONV_2D_SK_P0 = 51
GGML_OP_FLASH_ATTN = 52
GGML_OP_FLASH_FF = 53
GGML_OP_FLASH_ATTN_BACK = 54
GGML_OP_WIN_PART = 55
GGML_OP_WIN_UNPART = 56
GGML_OP_MAP_UNARY = 57
GGML_OP_MAP_BINARY = 58
GGML_OP_MAP_CUSTOM1 = 59
GGML_OP_MAP_CUSTOM2 = 60
GGML_OP_MAP_CUSTOM3 = 61
GGML_OP_CROSS_ENTROPY_LOSS = 62
GGML_OP_CROSS_ENTROPY_LOSS_BACK = 63
GGML_OP_COUNT = 64

# struct ggml_object {
#     size_t offs;
#     size_t size;

#     struct ggml_object * next;


#     char padding[8];
# };
class ggml_object(ctypes.Structure):
    pass


ggml_object._fields_ = [
    ("offs", ctypes.c_size_t),
    ("size", ctypes.c_size_t),
    ("next", ctypes.POINTER(ggml_object)),
    ("padding", ctypes.c_char * 8),
]

ggml_object_p: TypeAlias = "ctypes._Pointer[ggml_object]"  # type: ignore

GGML_OBJECT_SIZE = ctypes.sizeof(ggml_object)


# // n-dimensional tensor
# struct ggml_tensor {
#     enum ggml_type    type;
#     enum ggml_backend backend;

#     int     n_dims;
#     int64_t ne[GGML_MAX_DIMS]; // number of elements
#     size_t  nb[GGML_MAX_DIMS]; // stride in bytes:
#                                 // nb[0] = sizeof(type)
#                                 // nb[1] = nb[0]   * ne[0] + padding
#                                 // nb[i] = nb[i-1] * ne[i-1]

#     // compute data
#     enum ggml_op op;

#     bool is_param;

#     struct ggml_tensor * grad;
#     struct ggml_tensor * src0;
#     struct ggml_tensor * src1;
#     struct ggml_tensor * opt[GGML_MAX_OPT];

#     // thread scheduling
#     int n_tasks;

#     // performance
#     int     perf_runs;
#     int64_t perf_cycles;
#     int64_t perf_time_us;

#     void * data;

#     char name[GGML_MAX_NAME];

#     void * extra; // extra things e.g. for ggml-cuda.cu


#     char padding[4];
# };
class ggml_tensor(ctypes.Structure):
    """n-dimensional tensor

    Attributes:
        type (int): ggml_type
        backend (int): ggml_backend
        n_dims (int): number of dimensions
        ne (ctypes.Array[ctypes.c_int64]): number of elements in each dimension
        nb (ctypes.Array[ctypes.c_size_t]): stride in bytes for each dimension
        op (int): ggml operation
        is_param (bool): is this a parameter tensor
        grad (ggml_tensor_p): reference to gradient tensor
        src0 (ggml_tensor_p): reference to source tensor 0
        src1 (ggml_tensor_p): reference to source tensor 1
        opt (ctypes.Array[ggml_tensor_p]): optimization tensors
        n_tasks (int): number of tasks
        perf_runs (int): number of performance runs
        perf_cycles (int): number of cycles
        perf_time_us (int): time in microseconds
        data (ctypes.c_void_p): reference to raw tensor data
        name (bytes): name of tensor
        extra (ctypes.c_void_p): extra data (e.g. for CUDA)
    """

    pass


ggml_tensor._fields_ = [
    ("type", ctypes.c_int),
    ("backend", ctypes.c_int),
    ("n_dims", ctypes.c_int),
    ("ne", ctypes.c_int64 * GGML_MAX_DIMS),
    ("nb", ctypes.c_size_t * GGML_MAX_DIMS),
    ("op", ctypes.c_int),
    ("is_param", ctypes.c_bool),
    ("grad", ctypes.POINTER(ggml_tensor)),
    ("src0", ctypes.POINTER(ggml_tensor)),
    ("src1", ctypes.POINTER(ggml_tensor)),
    ("opt", ctypes.POINTER(ggml_tensor) * GGML_MAX_OPT),
    ("n_tasks", ctypes.c_int),
    ("perf_runs", ctypes.c_int),
    ("perf_cycles", ctypes.c_int64),
    ("perf_time_us", ctypes.c_int64),
    ("data", ctypes.c_void_p),
    ("name", ctypes.c_char * GGML_MAX_NAME),
    ("extra", ctypes.c_void_p),
    ("padding", ctypes.c_char * 4),
]

GGML_TENSOR_SIZE = ctypes.sizeof(ggml_tensor)

ggml_tensor_p: TypeAlias = "ctypes._Pointer[ggml_tensor]"  # type: ignore
"""ctypes pointer to a [ggml_tensor][ggml.ggml_tensor]

Can be dereferenced to a [ggml_tensor][ggml.ggml_tensor] object using
the `.contents` attribute."""

# // computation graph
# struct ggml_cgraph {
#     int n_nodes;
#     int n_leafs;
#     int n_threads;

#     size_t work_size;
#     struct ggml_tensor * work;

#     struct ggml_tensor * nodes[GGML_MAX_NODES];
#     struct ggml_tensor * grads[GGML_MAX_NODES];
#     struct ggml_tensor * leafs[GGML_MAX_NODES];


#     // performance
#     int     perf_runs;
#     int64_t perf_cycles;
#     int64_t perf_time_us;
# };
class ggml_cgraph(ctypes.Structure):
    """ggml computation graph
    
    Attributes:
        n_nodes (int): number of nodes
        n_leafs (int): number of leafs
        n_threads (int): number of threads to use when computing the graph using [ggml_graph_compute][ggml.ggml_graph_compute]
        work_size (int): size of work buffer
        work (ggml_tensor_p): work buffer
        nodes (ctypes.Array[ggml_tensor_p]): `n_nodes`-length array of compute tensors
        grads (ctypes.Array[ggml_tensor_p]): `n_nodes`-length array of gradient tensors
        leafs (ctypes.Array[ggml_tensor_p]): `n_leafs`-length array of parameter tensors
        perf_runs (int): number of runs
        perf_cycles (int): number of cycles
        perf_time_us (int): computation time in microseconds"""

    _fields_ = [
        ("n_nodes", ctypes.c_int),
        ("n_leafs", ctypes.c_int),
        ("n_threads", ctypes.c_int),
        ("work_size", ctypes.c_size_t),
        ("work", ctypes.POINTER(ggml_tensor)),
        ("nodes", ctypes.POINTER(ggml_tensor) * GGML_MAX_NODES),
        ("grads", ctypes.POINTER(ggml_tensor) * GGML_MAX_NODES),
        ("leafs", ctypes.POINTER(ggml_tensor) * GGML_MAX_NODES),
        ("perf_runs", ctypes.c_int),
        ("perf_cycles", ctypes.c_int64),
        ("perf_time_us", ctypes.c_int64),
    ]

ggml_cgraph_p: TypeAlias = "ctypes._Pointer[ggml_cgraph]"  # type: ignore
"""ctypes pointer to a [ggml_cgraph][ggml.ggml_cgraph]

Can be dereferenced to a [ggml_cgraph][ggml.ggml_cgraph] object using
the `.contents` attribute."""


# struct ggml_scratch {
#     size_t offs;
#     size_t size;
#     void * data;
# };
class ggml_scratch(ctypes.Structure):
    _fields_ = [
        ("offs", ctypes.c_size_t),
        ("size", ctypes.c_size_t),
        ("data", ctypes.c_void_p),
    ]


# struct ggml_init_params {
#     // memory pool
#     size_t mem_size;   // bytes
#     void * mem_buffer; // if NULL, memory will be allocated internally
#     bool   no_alloc;   // don't allocate memory for the tensor data
# };
class ggml_init_params(ctypes.Structure):
    """Initialization parameters for a ggml context

    **NOTE**: Reference counting does not cross into ggml, if you allocate a memory buffer
    in python using ctypes Arrays or a numpy array, you must keep a reference to it until
    you free the ggml context otherwise you will encounter a segmentation fault. 

    Attributes:
        mem_size (int): size of memory pool in bytes
        mem_buffer (ctypes.c_void_p): pointer to memory pool, if None, memory will be allocated internally
        no_alloc (bool): don't allocate memory for tensor data
    """

    _fields_ = [
        ("mem_size", ctypes.c_size_t),
        ("mem_buffer", ctypes.c_void_p),
        ("no_alloc", ctypes.c_bool),
    ]


# // compute types
# enum ggml_task_type {
#     GGML_TASK_INIT = 0,
#     GGML_TASK_COMPUTE,
#     GGML_TASK_FINALIZE,
# };
GGML_TASK_INIT = 0
GGML_TASK_COMPUTE = 1
GGML_TASK_FINALIZE = 2

# struct ggml_compute_params {
#     enum ggml_task_type type;

#     // ith = thread index, nth = number of threads
#     int ith, nth;


#     // work buffer for all threads
#     size_t wsize;
#     void * wdata;
# };
class ggml_compute_params(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("ith", ctypes.c_int),
        ("nth", ctypes.c_int),
        ("wsize", ctypes.c_size_t),
        ("wdata", ctypes.c_void_p),
    ]

# // misc

# GGML_API void    ggml_time_init(void); // call this once at the beginning of the program
def ggml_time_init():
    return lib.ggml_time_init()


lib.ggml_time_init.argtypes = []
lib.ggml_time_init.restype = None


# GGML_API int64_t ggml_time_ms(void);
def ggml_time_ms() -> int:
    return lib.ggml_time_ms()


lib.ggml_time_ms.argtypes = []
lib.ggml_time_ms.restype = ctypes.c_int64


# GGML_API int64_t ggml_time_us(void);
def ggml_time_us() -> int:
    return lib.ggml_time_us()


lib.ggml_time_us.argtypes = []
lib.ggml_time_us.restype = ctypes.c_int64


# GGML_API int64_t ggml_cycles(void);
def ggml_cycles() -> int:
    return lib.ggml_cycles()


lib.ggml_cycles.argtypes = []
lib.ggml_cycles.restype = ctypes.c_int64


# GGML_API int64_t ggml_cycles_per_ms(void);
def ggml_cycles_per_ms() -> int:
    return lib.ggml_cycles_per_ms()


lib.ggml_cycles_per_ms.argtypes = []
lib.ggml_cycles_per_ms.restype = ctypes.c_int64

# GGML_API void    ggml_numa_init(void); // call once for better performance on NUMA systems
def ggml_numa_init():
    return lib.ggml_numa_init()

lib.ggml_numa_init.argtypes = []
lib.ggml_numa_init.restype = None

# GGML_API bool    ggml_is_numa(void); // true if init detected that system has >1 NUMA node
def ggml_is_numa() -> bool:
    return lib.ggml_is_numa()

lib.ggml_is_numa.argtypes = []
lib.ggml_is_numa.restype = ctypes.c_bool

# GGML_API void    ggml_print_object (const struct ggml_object * obj);
def ggml_print_object(obj: ggml_object_p):  
    return lib.ggml_print_object(obj)


lib.ggml_print_object.argtypes = [ctypes.POINTER(ggml_object)]
lib.ggml_print_object.restype = None


# GGML_API void    ggml_print_objects(const struct ggml_context * ctx);
def ggml_print_objects(ctx: ggml_context_p):
    return lib.ggml_print_objects(ctx)


lib.ggml_print_objects.argtypes = [ggml_context_p]
lib.ggml_print_objects.restype = None


# GGML_API int64_t ggml_nelements   (const struct ggml_tensor * tensor);
def ggml_nelements(
    tensor: ggml_tensor_p,  
) -> int:
    """Get the number of elements in a tensor
    
    Parameters:
        tensor: tensor
    
    Returns:
        number of elements"""
    return lib.ggml_nelements(tensor)


lib.ggml_nelements.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_nelements.restype = ctypes.c_int64


# GGML_API int64_t ggml_nrows       (const struct ggml_tensor * tensor);
def ggml_nrows(
    tensor: ggml_tensor_p,  
) -> int:
    """Get the number of rows in a tensor

    Parameters:
        tensor: tensor
    
    Returns:
        number of rows"""
    return lib.ggml_nrows(tensor)


lib.ggml_nrows.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_nrows.restype = ctypes.c_int64


# GGML_API size_t  ggml_nbytes      (const struct ggml_tensor * tensor);
def ggml_nbytes(
    tensor: ggml_tensor_p,  
) -> int:
    """Get the number of bytes required to store tensor data

    Parameters:
        tensor: tensor
    
    Returns:
        number of bytes"""
    return lib.ggml_nbytes(tensor)


lib.ggml_nbytes.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_nbytes.restype = ctypes.c_size_t


# GGML_API size_t  ggml_nbytes_split(const struct ggml_tensor * tensor, int nrows_split);
def ggml_nbytes_split(
    tensor: ggml_tensor_p,  
    nrows_split: Union[ctypes.c_int, int],
) -> int:
    return lib.ggml_nbytes_split(tensor, nrows_split)


lib.ggml_nbytes_split.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_int]
lib.ggml_nbytes_split.restype = ctypes.c_size_t


# GGML_API int     ggml_blck_size (enum ggml_type type);
def ggml_blck_size(type: Union[ctypes.c_int, int]) -> int:
    return lib.ggml_blck_size(type)


lib.ggml_blck_size.argtypes = [ctypes.c_int]
lib.ggml_blck_size.restype = ctypes.c_int


# GGML_API size_t  ggml_type_size (enum ggml_type type); // size in bytes for all elements in a block
def ggml_type_size(type: Union[ctypes.c_int, int]) -> int:
    return lib.ggml_type_size(type)


lib.ggml_type_size.argtypes = [ctypes.c_int]
lib.ggml_type_size.restype = ctypes.c_size_t


# GGML_API float   ggml_type_sizef(enum ggml_type type); // ggml_type_size()/ggml_blck_size() as float
def ggml_type_sizef(type: Union[ctypes.c_int, int]) -> float:
    return lib.ggml_type_sizef(type)


lib.ggml_type_sizef.argtypes = [ctypes.c_int]
lib.ggml_type_sizef.restype = ctypes.c_float


# GGML_API const char * ggml_type_name(enum ggml_type type);
def ggml_type_name(type: Union[ctypes.c_int, int]) -> bytes:
    return lib.ggml_type_name(type)


lib.ggml_type_name.argtypes = [ctypes.c_int]
lib.ggml_type_name.restype = ctypes.c_char_p


# GGML_API const char * ggml_op_name  (enum ggml_op   op);
def ggml_op_name(op: Union[ctypes.c_int, int]) -> bytes:
    return lib.ggml_op_name(op)


lib.ggml_op_name.argtypes = [ctypes.c_int]
lib.ggml_op_name.restype = ctypes.c_char_p


# GGML_API size_t  ggml_element_size(const struct ggml_tensor * tensor);
def ggml_element_size(
    tensor: ggml_tensor_p,  
) -> int:  
    return lib.ggml_element_size(tensor)


lib.ggml_element_size.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_element_size.restype = ctypes.c_size_t


# GGML_API bool    ggml_is_quantized(enum ggml_type type);
def ggml_is_quantized(type: Union[ctypes.c_int, int]) -> bool:
    return lib.ggml_is_quantized(type)


lib.ggml_is_quantized.argtypes = [ctypes.c_int]
lib.ggml_is_quantized.restype = ctypes.c_bool


# // TODO: temporary until model loading of ggml examples is refactored
# GGML_API enum ggml_type ggml_ftype_to_ggml_type(enum ggml_ftype ftype);
def ggml_ftype_to_ggml_type(ftype: Union[ctypes.c_int, int]) -> int:
    return lib.ggml_ftype_to_ggml_type(ftype)


lib.ggml_ftype_to_ggml_type.argtypes = [ctypes.c_int]
lib.ggml_ftype_to_ggml_type.restype = ctypes.c_int


# GGML_API bool ggml_is_transposed(const struct ggml_tensor * tensor);
def ggml_is_transposed(
    tensor: ggml_tensor_p,  
) -> bool:
    """Check if a tensor is transposed
    
    Parameters:
        tensor: tensor
    
    Returns:
        True if tensor is transposed else False"""
    return lib.ggml_is_transposed(tensor)


lib.ggml_is_transposed.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_is_transposed.restype = ctypes.c_bool


# GGML_API bool ggml_is_contiguous(const struct ggml_tensor * tensor);
def ggml_is_contiguous(
    tensor: ggml_tensor_p,  
) -> bool:
    """Check if a tensor is contiguous

    Parameters:
        tensor: tensor

    Returns:
        True if tensor is contiguous else False"""
    return lib.ggml_is_contiguous(tensor)


lib.ggml_is_contiguous.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_is_contiguous.restype = ctypes.c_bool


# GGML_API bool ggml_is_permuted  (const struct ggml_tensor * tensor);
def ggml_is_permuted(
    tensor: ggml_tensor_p,  
) -> bool:
    """Check if a tensor is permuted

    Parameters:
        tensor: tensor

    Returns:
        True if tensor is permuted else False"""
    return lib.ggml_is_permuted(tensor)


lib.ggml_is_permuted.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_is_permuted.restype = ctypes.c_bool


# // use this to compute the memory overhead of a tensor
# GGML_API size_t ggml_tensor_overhead(void);
def ggml_tensor_overhead() -> int:
    """Overhead required for a tensor struct in bytes
    
    Returns:
        size of tensor struct in bytes"""
    return lib.ggml_tensor_overhead()


lib.ggml_tensor_overhead.argtypes = []
lib.ggml_tensor_overhead.restype = ctypes.c_size_t

# // main


# GGML_API struct ggml_context * ggml_init(struct ggml_init_params params);
def ggml_init(
    params: ggml_init_params,
) -> ggml_context_p:
    """Instantiate a new ggml context with params.

    You must call `ggml_free()` to free the context.

    Parameters:
        params: ggml init params

    Returns:
        Pointer to ggml_context"""
    return lib.ggml_init(params)


lib.ggml_init.argtypes = [ggml_init_params]
lib.ggml_init.restype = ggml_context_p


# GGML_API void                  ggml_free(struct ggml_context * ctx);
def ggml_free(ctx: ggml_context_p):
    """Free the ggml context.
    
    Parameters:
        ctx: ggml context"""
    return lib.ggml_free(ctx)


lib.ggml_free.argtypes = [ggml_context_p]
lib.ggml_free.restype = None


# GGML_API size_t  ggml_used_mem(const struct ggml_context * ctx);
def ggml_used_mem(ctx: ggml_context_p) -> int:
    """Return the amount of memory used by the ggml context in bytes.
    
    Parameters:
        ctx: ggml context
    
    Returns:
        amount of memory used in bytes"""
    return lib.ggml_used_mem(ctx)


lib.ggml_used_mem.argtypes = [ggml_context_p]
lib.ggml_used_mem.restype = ctypes.c_size_t


# GGML_API size_t  ggml_set_scratch(struct ggml_context * ctx, struct ggml_scratch scratch);
def ggml_set_scratch(ctx: ggml_context_p, scratch: ggml_scratch) -> int:
    """Set the scratch buffer for the ggml context."""
    return lib.ggml_set_scratch(ctx, scratch)


lib.ggml_set_scratch.argtypes = [ggml_context_p, ggml_scratch]
lib.ggml_set_scratch.restype = ctypes.c_size_t


# GGML_API void    ggml_set_no_alloc(struct ggml_context * ctx, bool no_alloc);
def ggml_set_no_alloc(ctx: ggml_context_p, no_alloc: Union[ctypes.c_bool, bool]):
    """Set the no_alloc flag for the ggml context."""
    return lib.ggml_set_no_alloc(ctx, no_alloc)


lib.ggml_set_no_alloc.argtypes = [ggml_context_p, ctypes.c_bool]
lib.ggml_set_no_alloc.restype = None


# GGML_API void *  ggml_get_mem_buffer     (struct ggml_context * ctx);
def ggml_get_mem_buffer(ctx: ggml_context_p) -> Optional[ctypes.c_void_p]:
    """Return the memory buffer for the ggml context."""
    return lib.ggml_get_mem_buffer(ctx)


lib.ggml_get_mem_buffer.argtypes = [ggml_context_p]
lib.ggml_get_mem_buffer.restype = ctypes.c_void_p


# GGML_API size_t  ggml_get_mem_size       (struct ggml_context * ctx);
def ggml_get_mem_size(ctx: ggml_context_p) -> int:
    """Return the size of the memory buffer for the ggml context in bytes."""
    return lib.ggml_get_mem_size(ctx)


lib.ggml_get_mem_size.argtypes = [ggml_context_p]
lib.ggml_get_mem_size.restype = ctypes.c_size_t


# GGML_API size_t  ggml_get_max_tensor_size(const struct ggml_context * ctx);
def ggml_get_max_tensor_size(ctx: ggml_context_p) -> int:
    """Return the maximum size of a tensor in bytes."""
    return lib.ggml_get_max_tensor_size(ctx)


lib.ggml_get_max_tensor_size.argtypes = [ggml_context_p]
lib.ggml_get_max_tensor_size.restype = ctypes.c_size_t


# GGML_API struct ggml_tensor * ggml_new_tensor(
#         struct ggml_context * ctx,
#         enum   ggml_type type,
#         int    n_dims,
#         const int64_t *ne);
def ggml_new_tensor(
    ctx: ggml_context_p,
    type: Union[ctypes.c_int, int],
    n_dims: Union[ctypes.c_int, int],
    ne,  # type: ctypes.Array[ctypes.c_int64] # type: ignore
) -> ggml_tensor_p:  
    """Create a new tensor with the given type, number of dimensions, and number of elements in each dimension.
    
    Parameters:
        ctx: ggml context
        type: ggml type
        n_dims: number of dimensions
        ne (ctypes.Array[ctypes.c_int64]): number of elements in each dimension (array of length n_dims)
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_tensor(ctx, type, n_dims, ne)


lib.ggml_new_tensor.argtypes = [
    ggml_context_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_new_tensor.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_tensor_1d(
#         struct ggml_context * ctx,
#         enum   ggml_type type,
#         int64_t ne0);
def ggml_new_tensor_1d(
    ctx: ggml_context_p, type: Union[ctypes.c_int, int], ne0: Union[ctypes.c_int64, int]
) -> ggml_tensor_p:
    """Create a new 1-dimensional tensor with the given type and number of elements.
    
    Parameters:
        ctx: ggml context
        type: ggml type
        ne0: number of elements in dimension 0
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_tensor_1d(ctx, type, ne0)


lib.ggml_new_tensor_1d.argtypes = [ggml_context_p, ctypes.c_int, ctypes.c_int64]
lib.ggml_new_tensor_1d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_tensor_2d(
#         struct ggml_context * ctx,
#         enum   ggml_type type,
#         int64_t ne0,
#         int64_t ne1);
def ggml_new_tensor_2d(
    ctx: ggml_context_p,
    type: Union[ctypes.c_int, int],
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:
    """Create a new 2-dimensional tensor with the given type and number of elements in each dimension.
    
    Parameters:
        ctx: ggml context
        type: ggml type
        ne0: number of elements in dimension 0
        ne1: number of elements in dimension 1
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_tensor_2d(ctx, type, ne0, ne1)


lib.ggml_new_tensor_2d.argtypes = [
    ggml_context_p,
    ctypes.c_int,
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_new_tensor_2d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_tensor_3d(
#         struct ggml_context * ctx,
#         enum   ggml_type type,
#         int64_t ne0,
#         int64_t ne1,
#         int64_t ne2);
def ggml_new_tensor_3d(
    ctx: ggml_context_p,
    type: Union[ctypes.c_int, int],
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:
    """Create a new 3-dimensional tensor with the given type and number of elements in each dimension.
    
    Parameters:
        ctx: ggml context
        type: ggml type
        ne0: number of elements in dimension 0
        ne1: number of elements in dimension 1
        ne2: number of elements in dimension 2
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_tensor_3d(ctx, type, ne0, ne1, ne2)


lib.ggml_new_tensor_3d.argtypes = [
    ggml_context_p,
    ctypes.c_int,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_new_tensor_3d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_tensor_4d(
#         struct ggml_context * ctx,
#         enum   ggml_type type,
#         int64_t ne0,
#         int64_t ne1,
#         int64_t ne2,
#         int64_t ne3);
def ggml_new_tensor_4d(
    ctx: ggml_context_p,
    type: Union[ctypes.c_int, int],
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
    ne3: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:
    """Create a new 4-dimensional tensor with the given type and number of elements in each dimension.

    Parameters:
        ctx: ggml context
        type: ggml type
        ne0: number of elements in dimension 0
        ne1: number of elements in dimension 1
        ne2: number of elements in dimension 2
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_tensor_4d(ctx, type, ne0, ne1, ne2, ne3)


lib.ggml_new_tensor_4d.argtypes = [
    ggml_context_p,
    ctypes.c_int,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_new_tensor_4d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_i32(struct ggml_context * ctx, int32_t value);
def ggml_new_i32(
    ctx: ggml_context_p, value: Union[ctypes.c_int32, int]
) -> ggml_tensor_p:
    """Create a 1 element tensor with the given integer value.
    
    Parameters:
        ctx: ggml context
        value: integer value

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_i32(ctx, value)


lib.ggml_new_i32.argtypes = [ggml_context_p, ctypes.c_int32]
lib.ggml_new_i32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_new_f32(struct ggml_context * ctx, float value);
def ggml_new_f32(
    ctx: ggml_context_p,
    value: Union[ctypes.c_float, float],
) -> ggml_tensor_p:
    """Create a 1 element tensor with the given float value.

    Parameters:
        ctx: ggml context
        value: float value

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_new_f32(ctx, value)


lib.ggml_new_f32.argtypes = [ggml_context_p, ctypes.c_float]
lib.ggml_new_f32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_dup_tensor (struct ggml_context * ctx, const struct ggml_tensor * src);
def ggml_dup_tensor(
    ctx: ggml_context_p, src: ggml_tensor_p  
) -> ggml_tensor_p:
    """Create a new tensor with the same type and dimensions as the source tensor.
    
    Parameters:
        ctx: ggml context
        src: source tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_dup_tensor(ctx, src)


lib.ggml_dup_tensor.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_dup_tensor.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_view_tensor(struct ggml_context * ctx, const struct ggml_tensor * src);
def ggml_view_tensor(
    ctx: ggml_context_p, src: ggml_tensor_p  
) -> ggml_tensor_p:
    """Create a new tensor with the same type, dimensions and data as the source tensor.

    Parameters:
        ctx: ggml context
        src: source tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_view_tensor(ctx, src)


lib.ggml_view_tensor.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_view_tensor.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_get_tensor(struct ggml_context * ctx, const char * name);
def ggml_get_tensor(
    ctx: ggml_context_p, name: bytes
) -> ggml_tensor_p:
    """Get a tensor from the ggml context by name.
    
    Parameters:
        ctx: ggml context
        name: name of tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_get_tensor(ctx, name)


lib.ggml_get_tensor.argtypes = [ggml_context_p, ctypes.c_char_p]
lib.ggml_get_tensor.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_set_zero(struct ggml_tensor * tensor);
def ggml_set_zero(
    tensor: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Zero all elements in a tensor.
    
    Parameters:
        tensor: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_set_zero(tensor)


lib.ggml_set_zero.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_set_zero.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_set_i32 (struct ggml_tensor * tensor, int32_t value);
def ggml_set_i32(
    tensor: ggml_tensor_p,  
    value: Union[ctypes.c_int32, int],
) -> ggml_tensor_p:
    """Set all elements in a tensor to the given integer value.
    
    Parameters:
        tensor: tensor
        value: integer value

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_set_i32(tensor, value)


lib.ggml_set_i32.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_int32]
lib.ggml_set_i32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_set_f32 (struct ggml_tensor * tensor, float value);
def ggml_set_f32(
    tensor: ggml_tensor_p,  
    value: Union[ctypes.c_float, float],
) -> ggml_tensor_p:
    """Set all elements in a tensor to the given float value.
    
    Parameters:
        tensor: tensor
        value: float value

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_set_f32(tensor, value)


lib.ggml_set_f32.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_float]
lib.ggml_set_f32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API int32_t ggml_get_i32_1d(const struct ggml_tensor * tensor, int i);
def ggml_get_i32_1d(
    tensor: ggml_tensor_p,  
    i: Union[ctypes.c_int, int],
) -> int:
    """Get the integer value of the i-th element in a 1-dimensional tensor.
    
    Parameters:
        tensor: tensor
        i: index of element

    Returns:
        integer value of element at index i"""
    return lib.ggml_get_i32_1d(tensor, i)


lib.ggml_get_i32_1d.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_int]
lib.ggml_get_i32_1d.restype = ctypes.c_int32


# GGML_API void    ggml_set_i32_1d(const struct ggml_tensor * tensor, int i, int32_t value);
def ggml_set_i32_1d(
    tensor: ggml_tensor_p,  
    i: Union[ctypes.c_int, int],
    value: Union[ctypes.c_int32, int],
):
    """Set the integer value of the i-th element in a 1-dimensional tensor.

    Parameters:
        tensor: tensor
        i: index of element
        value: integer value to set element to"""
    return lib.ggml_set_i32_1d(tensor, i, value)


lib.ggml_set_i32_1d.argtypes = [
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int32,
]
lib.ggml_set_i32_1d.restype = None


# GGML_API float   ggml_get_f32_1d(const struct ggml_tensor * tensor, int i);
def ggml_get_f32_1d(
    tensor: ggml_tensor_p,  
    i: Union[ctypes.c_int, int],
) -> float:
    """Get the float value of the i-th element in a 1-dimensional tensor.
    
    Parameters:
        tensor: tensor

    Returns:
        float value of element at index i"""
    return lib.ggml_get_f32_1d(tensor, i)


lib.ggml_get_f32_1d.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_int]
lib.ggml_get_f32_1d.restype = ctypes.c_float


# GGML_API void    ggml_set_f32_1d(const struct ggml_tensor * tensor, int i, float value);
def ggml_set_f32_1d(
    tensor: ggml_tensor_p,  
    i: Union[ctypes.c_int, int],
    value: Union[ctypes.c_float, float],
):
    """Set the float value of the i-th element in a 1-dimensional tensor.

    Parameters:
        tensor: tensor
        i: index of element
        value: float value to set element to"""
    return lib.ggml_set_f32_1d(tensor, i, value)


lib.ggml_set_f32_1d.argtypes = [
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_float,
]
lib.ggml_set_f32_1d.restype = None


# GGML_API void *  ggml_get_data    (const struct ggml_tensor * tensor);
def ggml_get_data(
    tensor: ggml_tensor_p,  
) -> Optional[ctypes.c_void_p]:
    """Get the data pointer of a tensor.
    
    Parameters:
        tensor: tensor

    Returns:
        Pointer to data, or None if tensor has no data"""
    return lib.ggml_get_data(tensor)


lib.ggml_get_data.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_get_data.restype = ctypes.c_void_p


# GGML_API float * ggml_get_data_f32(const struct ggml_tensor * tensor);
def ggml_get_data_f32(
    tensor: ggml_tensor_p,  
):  # type: (...) -> Optional[ctypes.Array[ctypes.c_float]] # type: ignore
    """Get the data pointer of a tensor as a float array.
    
    Parameters:
        tensor: tensor

    Returns:
        (Optional[ctypes.Array[ctypes.c_float]]): array of float to data, or None if tensor has no data"""
    return lib.ggml_get_data_f32(tensor)


lib.ggml_get_data_f32.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_get_data_f32.restype = ctypes.POINTER(ctypes.c_float)


# GGML_API const char *         ggml_get_name(const struct ggml_tensor * tensor);
def ggml_get_name(
    tensor: ggml_tensor_p,  
) -> bytes:
    """Get the name of a tensor.

    Parameters:
        tensor: tensor

    Returns:
        name of tensor"""
    return lib.ggml_get_name(tensor)


lib.ggml_get_name.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_get_name.restype = ctypes.c_char_p


# GGML_API struct ggml_tensor * ggml_set_name(struct ggml_tensor * tensor, const char * name);
def ggml_set_name(
    tensor: ggml_tensor_p,  
    name: bytes,
) -> ggml_tensor_p:
    """Set the name of a tensor.

    Parameters:
        tensor: tensor
        name: name to set tensor to

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_set_name(tensor, name)


lib.ggml_set_name.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_char_p]
lib.ggml_set_name.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_format_name(struct ggml_tensor * tensor, const char * fmt, ...);
def ggml_format_name(
    tensor: ggml_tensor_p,
    fmt: bytes,
    *args: Sequence[Union[bool, int, float, str]],
) -> ggml_tensor_p:
    """Format the name of a tensor using the given format c string and arguments.

    Parameters:
        tensor: tensor
        fmt: format c string
        args: arguments to format string

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_format_name(tensor, fmt, *args)

lib.ggml_format_name.argtypes = [ctypes.POINTER(ggml_tensor), ctypes.c_char_p]
lib.ggml_format_name.restype = ctypes.POINTER(ggml_tensor)

# //
# // operations on tensors with backpropagation
# //

# GGML_API struct ggml_tensor * ggml_dup(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_dup(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    return lib.ggml_dup(ctx, a)


lib.ggml_dup.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_dup.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_add(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_add(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Add two tensors together and return the result.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_add(ctx, a, b)


lib.ggml_add.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_add.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_add_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_add_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Add two tensors together and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_add_inplace(ctx, a, b)


lib.ggml_add_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_add_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_add1(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_add1(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_add1(ctx, a, b)


lib.ggml_add1.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_add1.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_add1_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_add1_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_add1_inplace(ctx, a, b)


lib.ggml_add1_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_add1_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_acc(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                nb2,
#         size_t                nb3,
#         size_t                offset);
def ggml_acc(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    nb3: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_acc(ctx, a, b, nb1, nb2, nb3, offset)


lib.ggml_acc.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_acc.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_acc_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                nb2,
#         size_t                nb3,
#         size_t                offset);
def ggml_acc_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    nb3: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_acc_inplace(ctx, a, b, nb1, nb2, nb3, offset)


lib.ggml_acc_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_acc_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sub(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_sub(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Subtract two tensors and return the result.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sub(ctx, a, b)


lib.ggml_sub.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_sub.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sub_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_sub_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Subtract two tensors and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sub_inplace(ctx, a, b)


lib.ggml_sub_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_sub_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_mul(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_mul(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Element-wise multiply two tensors and return the result.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_mul(ctx, a, b)


lib.ggml_mul.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_mul.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_mul_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_mul_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Element-wise multiply two tensors and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_mul_inplace(ctx, a, b)


lib.ggml_mul_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_mul_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_div(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_div(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Element-wise divide two tensors and return the result.
    
    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_div(ctx, a, b)


lib.ggml_div.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_div.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_div_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_div_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Element-wise divide two tensors and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: first tensor
        b: second tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_div_inplace(ctx, a, b)


lib.ggml_div_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_div_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sqr(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sqr(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Square all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sqr(ctx, a)


lib.ggml_sqr.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sqr.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sqr_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sqr_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Square all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sqr_inplace(ctx, a)


lib.ggml_sqr_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sqr_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sqrt(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sqrt(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Square root all elements in a tensor and return the result.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sqrt(ctx, a)


lib.ggml_sqrt.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sqrt.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sqrt_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sqrt_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Square root all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sqrt_inplace(ctx, a)


lib.ggml_sqrt_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sqrt_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_log(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_log(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Take the natural logarithm of all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_log(ctx, a)


lib.ggml_log.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_log.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_log_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_log_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Take the natural logarithm of all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_log_inplace(ctx, a)


lib.ggml_log_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_log_inplace.restype = ctypes.POINTER(ggml_tensor)


# // return scalar
# GGML_API struct ggml_tensor * ggml_sum(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sum(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Sum all elements in a tensor and return the result.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sum(ctx, a)


lib.ggml_sum.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sum.restype = ctypes.POINTER(ggml_tensor)


# // sums along rows, with input shape [a,b,c,d] return shape [1,b,c,d]
# GGML_API struct ggml_tensor * ggml_sum_rows(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sum_rows(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Sum all elements in a tensor along the first axis and return the result.
    
    sums along rows, with input shape [a,b,c,d] return shape [1,b,c,d]
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sum_rows(ctx, a)


lib.ggml_sum_rows.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sum_rows.restype = ctypes.POINTER(ggml_tensor)


# // mean along rows
# GGML_API struct ggml_tensor * ggml_mean(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_mean(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Take the mean of all elements in a tensor and return the result.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_mean(ctx, a)


lib.ggml_mean.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_mean.restype = ctypes.POINTER(ggml_tensor)


# // if a is the same shape as b, and a is not parameter, return a
# // otherwise, return a new tensor: repeat(a) to fit in b
# GGML_API struct ggml_tensor * ggml_repeat(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_repeat(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Repeat a tensor to fit the shape of another tensor.

    If a is the same shape as b, and a is not parameter, return a

    Parameters:
        ctx: ggml context
        a: tensor to repeat
        b: tensor to fit

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_repeat(ctx, a, b)


lib.ggml_repeat.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_repeat.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_repeat_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_repeat_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_repeat_back(ctx, a, b)


lib.ggml_repeat_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_repeat_back.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_abs(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_abs(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Take the absolute value of all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_abs(ctx, a)


lib.ggml_abs.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_abs.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_abs_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_abs_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Take the absolute value of all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_abs_inplace(ctx, a)


lib.ggml_abs_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_abs_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sgn(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sgn(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Get the sign of all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sgn(ctx, a)


lib.ggml_sgn.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sgn.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_sgn_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_sgn_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Get the sign of all elements in a tensor and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_sgn_inplace(ctx, a)


lib.ggml_sgn_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_sgn_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_neg(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_neg(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Negate all elements in a tensor and return the result.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_neg(ctx, a)


lib.ggml_neg.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_neg.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_neg_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_neg_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Negate all elements in a tensor and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_neg_inplace(ctx, a)


lib.ggml_neg_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_neg_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_step(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_step(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    return lib.ggml_step(ctx, a)


lib.ggml_step.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_step.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_relu(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_relu(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p: 
    """Apply the ReLU activation function to all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_relu(ctx, a)


lib.ggml_relu.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_relu.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_relu_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_relu_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Apply the ReLU activation function to all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_relu_inplace(ctx, a)


lib.ggml_relu_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_relu_inplace.restype = ctypes.POINTER(ggml_tensor)


# // TODO: double-check this computation is correct
# GGML_API struct ggml_tensor * ggml_gelu(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_gelu(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Apply the Gaussian Error Linear Unit activation function to all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_gelu(ctx, a)


lib.ggml_gelu.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_gelu.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_gelu_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_gelu_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Apply the Gaussian Error Linear Unit activation function to all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_gelu_inplace(ctx, a)


lib.ggml_gelu_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_gelu_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_gelu_quick(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_gelu_quick(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Apply the Gaussian Error Linear Unit activation function to all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_gelu_quick(ctx, a)


lib.ggml_gelu_quick.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_gelu_quick.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_gelu_quick_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_gelu_quick_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Apply the Gaussian Error Linear Unit activation function to all elements in a tensor and store the result in the first tensor.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_gelu_quick_inplace(ctx, a)


lib.ggml_gelu_quick_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_gelu_quick_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_silu(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_silu(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Apply the Sigmoid Linear Unit activation function to all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor
    
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_silu(ctx, a)


lib.ggml_silu.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_silu.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_silu_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_silu_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Apply the Sigmoid Linear Unit activation function to all elements in a tensor and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_silu_inplace(ctx, a)


lib.ggml_silu_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_silu_inplace.restype = ctypes.POINTER(ggml_tensor)


# // a - x
# // b - dy
# GGML_API struct ggml_tensor * ggml_silu_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_silu_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_silu_back(ctx, a, b)


lib.ggml_silu_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_silu_back.restype = ctypes.POINTER(ggml_tensor)


# // normalize along rows
# // TODO: eps is hardcoded to 1e-5 for now
# GGML_API struct ggml_tensor * ggml_norm(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_norm(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    """Normalize all elements in a tensor along the first axis and return the result.
    
    normalize along rows.
    
    NOTE: eps is hardcoded to 1e-5 for now
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_norm(ctx, a)


lib.ggml_norm.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_norm.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_norm_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_norm_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Normalize all elements in a tensor along the first axis and store the result in the first tensor.
    
    normalize along rows.
    
    NOTE: eps is hardcoded to 1e-5 for now
    
    Parameters:
        ctx: ggml context
        a: tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_norm_inplace(ctx, a)


lib.ggml_norm_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_norm_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_rms_norm(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_rms_norm(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Compute the root mean square of all elements in a tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_rms_norm(ctx, a)


lib.ggml_rms_norm.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_rms_norm.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_rms_norm_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_rms_norm_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Compute the root mean square of all elements in a tensor and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_rms_norm_inplace(ctx, a)


lib.ggml_rms_norm_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_rms_norm_inplace.restype = ctypes.POINTER(ggml_tensor)


# // a - x
# // b - dy
# GGML_API struct ggml_tensor * ggml_rms_norm_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_rms_norm_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_rms_norm_back(ctx, a, b)


lib.ggml_rms_norm_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_rms_norm_back.restype = ctypes.POINTER(ggml_tensor)


# // A: m rows, n columns
# // B: p rows, n columns  (i.e. we transpose it internally)
# // result is m columns, p rows
# GGML_API struct ggml_tensor * ggml_mul_mat(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_mul_mat(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Multiply two matrices and return the result.
    
    A: m rows, n columns
    B: p rows, n columns  (i.e. we transpose it internally)
    result is m columns, p rows
    
    Parameters:
        ctx: ggml context
        a: tensor
        b: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_mul_mat(ctx, a, b)


lib.ggml_mul_mat.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_mul_mat.restype = ctypes.POINTER(ggml_tensor)


# // A: m columns, n rows,
# // B: p columns, n rows,
# // result is m columns, p rows
# GGML_API struct ggml_tensor * ggml_out_prod(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_out_prod(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Compute the outer product of two matrices and return the result.

    A: m columns, n rows,
    B: p columns, n rows,
    result is m columns, p rows

    Parameters:
        ctx: ggml context
        a: tensor
        b: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_out_prod(ctx, a, b)


lib.ggml_out_prod.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_out_prod.restype = ctypes.POINTER(ggml_tensor)

# //
# // operations on tensors without backpropagation
# //


# GGML_API struct ggml_tensor * ggml_scale(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_scale(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    """Scale a tensor by another tensor and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor
        b: tensor
        
    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_scale(ctx, a, b)


lib.ggml_scale.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_scale.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_scale_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_scale_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    """Scale a tensor by another tensor and store the result in the first tensor.

    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_scale_inplace(ctx, a, b)


lib.ggml_scale_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_scale_inplace.restype = ctypes.POINTER(ggml_tensor)


# // b -> view(a,offset,nb1,nb2,3), return modified a
# GGML_API struct ggml_tensor * ggml_set(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                nb2,
#         size_t                nb3,
#         size_t                offset);
def ggml_set(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    nb3: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set(ctx, a, b, nb1, nb2, nb3, offset)


lib.ggml_set.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_set.restype = ctypes.POINTER(ggml_tensor)


# // b -> view(a,offset,nb1,nb2,3), return view(a)
# GGML_API struct ggml_tensor * ggml_set_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                nb2,
#         size_t                nb3,
#         size_t                offset);
def ggml_set_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    nb3: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set_inplace(ctx, a, b, nb1, nb2, nb3, offset)


lib.ggml_set_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_set_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_set_1d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                offset);
def ggml_set_1d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set_1d(ctx, a, b, offset)


lib.ggml_set_1d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
]
lib.ggml_set_1d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_set_1d_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                offset);
def ggml_set_1d_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set_1d_inplace(ctx, a, b, offset)


lib.ggml_set_1d_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
]
lib.ggml_set_1d_inplace.restype = ctypes.POINTER(ggml_tensor)


# // b -> view(a,offset,nb1,nb2,3), return modified a
# GGML_API struct ggml_tensor * ggml_set_2d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                offset);
def ggml_set_2d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set_2d(ctx, a, b, nb1, offset)


lib.ggml_set_2d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_set_2d.restype = ctypes.POINTER(ggml_tensor)


# // b -> view(a,offset,nb1,nb2,3), return view(a)
# GGML_API struct ggml_tensor * ggml_set_2d_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         size_t                nb1,
#         size_t                offset);
def ggml_set_2d_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    nb1: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_set_2d_inplace(ctx, a, b, nb1, offset)


lib.ggml_set_2d_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_set_2d_inplace.restype = ctypes.POINTER(ggml_tensor)


# // a -> b, return view(b)
# GGML_API struct ggml_tensor * ggml_cpy(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_cpy(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_cpy(ctx, a, b)


lib.ggml_cpy.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_cpy.restype = ctypes.POINTER(ggml_tensor)


# // make contiguous
# GGML_API struct ggml_tensor * ggml_cont(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_cont(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:
    """Make a tensor contiguous and return the result.
    
    Parameters:
        ctx: ggml context
        a: tensor

    Returns:
        Pointer to ggml_tensor"""
    return lib.ggml_cont(ctx, a)


lib.ggml_cont.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_cont.restype = ctypes.POINTER(ggml_tensor)


# // return view(a), b specifies the new shape
# // TODO: when we start computing gradient, make a copy instead of view
# GGML_API struct ggml_tensor * ggml_reshape(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_reshape(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    return lib.ggml_reshape(ctx, a, b)


lib.ggml_reshape.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_reshape.restype = ctypes.POINTER(ggml_tensor)


# // return view(a)
# // TODO: when we start computing gradient, make a copy instead of view
# GGML_API struct ggml_tensor * ggml_reshape_1d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0);
def ggml_reshape_1d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:  
    return lib.ggml_reshape_1d(ctx, a, ne0)


lib.ggml_reshape_1d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
]
lib.ggml_reshape_1d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_reshape_2d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1);
def ggml_reshape_2d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:  
    return lib.ggml_reshape_2d(ctx, a, ne0, ne1)


lib.ggml_reshape_2d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_reshape_2d.restype = ctypes.POINTER(ggml_tensor)


# // return view(a)
# // TODO: when we start computing gradient, make a copy instead of view
# GGML_API struct ggml_tensor * ggml_reshape_3d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1,
#         int64_t               ne2);
def ggml_reshape_3d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:  
    return lib.ggml_reshape_3d(ctx, a, ne0, ne1, ne2)


lib.ggml_reshape_3d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_reshape_3d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_reshape_4d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1,
#         int64_t               ne2,
#         int64_t               ne3);
def ggml_reshape_4d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
    ne3: Union[ctypes.c_int64, int],
) -> ggml_tensor_p:  
    return lib.ggml_reshape_4d(ctx, a, ne0, ne1, ne2, ne3)


lib.ggml_reshape_4d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
]
lib.ggml_reshape_4d.restype = ctypes.POINTER(ggml_tensor)


# // offset in bytes
# GGML_API struct ggml_tensor * ggml_view_1d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         size_t                offset);
def ggml_view_1d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_view_1d(ctx, a, ne0, offset)


lib.ggml_view_1d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_size_t,
]
lib.ggml_view_1d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_view_2d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1,
#         size_t                nb1, // row stride in bytes
#         size_t                offset);
def ggml_view_2d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    nb1: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_view_2d(ctx, a, ne0, ne1, nb1, offset)


lib.ggml_view_2d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_view_2d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_view_3d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1,
#         int64_t               ne2,
#         size_t                nb1, // row   stride in bytes
#         size_t                nb2, // slice stride in bytes
#         size_t                offset);
def ggml_view_3d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_view_3d(ctx, a, ne0, ne1, ne2, nb1, nb2, offset)


lib.ggml_view_3d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_view_3d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_view_4d(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int64_t               ne0,
#         int64_t               ne1,
#         int64_t               ne2,
#         int64_t               ne3,
#         size_t                nb1, // row   stride in bytes
#         size_t                nb2, // slice stride in bytes
#         size_t                nb3,
#         size_t                offset);
def ggml_view_4d(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    ne0: Union[ctypes.c_int64, int],
    ne1: Union[ctypes.c_int64, int],
    ne2: Union[ctypes.c_int64, int],
    ne3: Union[ctypes.c_int64, int],
    nb1: Union[ctypes.c_size_t, int],
    nb2: Union[ctypes.c_size_t, int],
    nb3: Union[ctypes.c_size_t, int],
    offset: Union[ctypes.c_size_t, int],
) -> ggml_tensor_p:  
    return lib.ggml_view_4d(ctx, a, ne0, ne1, ne2, ne3, nb1, nb2, nb3, offset)


lib.ggml_view_4d.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_int64,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
lib.ggml_view_4d.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_permute(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   axis0,
#         int                   axis1,
#         int                   axis2,
#         int                   axis3);
def ggml_permute(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    axis0: Union[ctypes.c_int, int],
    axis1: Union[ctypes.c_int, int],
    axis2: Union[ctypes.c_int, int],
    axis3: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_permute(ctx, a, axis0, axis1, axis2, axis3)


lib.ggml_permute.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
lib.ggml_permute.restype = ctypes.POINTER(ggml_tensor)


# // alias for ggml_permute(ctx, a, 1, 0, 2, 3)
# GGML_API struct ggml_tensor * ggml_transpose(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_transpose(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    return lib.ggml_transpose(ctx, a)


lib.ggml_transpose.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_transpose.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_get_rows(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_get_rows(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    return lib.ggml_get_rows(ctx, a, b)


lib.ggml_get_rows.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_get_rows.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_get_rows_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b,
#         struct ggml_tensor  * c);
def ggml_get_rows_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    c: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_get_rows_back(ctx, a, b, c)


lib.ggml_get_rows_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_get_rows_back.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_diag(
#     struct ggml_context     * ctx,
#     struct ggml_tensor      * a);
def ggml_diag(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    return lib.ggml_diag(ctx, a)


lib.ggml_diag.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_diag.restype = ctypes.POINTER(ggml_tensor)


# // set elements above the diagonal to -INF
# GGML_API struct ggml_tensor * ggml_diag_mask_inf(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past);
def ggml_diag_mask_inf(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_diag_mask_inf(ctx, a, n_past)


lib.ggml_diag_mask_inf.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
]
lib.ggml_diag_mask_inf.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_diag_mask_inf_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past);
def ggml_diag_mask_inf_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_diag_mask_inf_inplace(ctx, a, n_past)


lib.ggml_diag_mask_inf_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
]
lib.ggml_diag_mask_inf_inplace.restype = ctypes.POINTER(ggml_tensor)


# // set elements above the diagonal to 0
# GGML_API struct ggml_tensor * ggml_diag_mask_zero(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past);
def ggml_diag_mask_zero(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_diag_mask_zero(ctx, a, n_past)


lib.ggml_diag_mask_zero.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
]
lib.ggml_diag_mask_zero.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_diag_mask_zero_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past);
def ggml_diag_mask_zero_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_diag_mask_zero_inplace(ctx, a, n_past)


lib.ggml_diag_mask_zero_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
]
lib.ggml_diag_mask_zero_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_soft_max(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_soft_max(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    return lib.ggml_soft_max(ctx, a)


lib.ggml_soft_max.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_soft_max.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_soft_max_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a);
def ggml_soft_max_inplace(
    ctx: ggml_context_p, a: ggml_tensor_p  
) -> ggml_tensor_p:  
    return lib.ggml_soft_max_inplace(ctx, a)


lib.ggml_soft_max_inplace.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_soft_max_inplace.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_soft_max_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_soft_max_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_soft_max_back(ctx, a, b)


lib.ggml_soft_max_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_soft_max_back.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_soft_max_back_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_soft_max_back_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_soft_max_back_inplace(ctx, a, b)


lib.ggml_soft_max_back_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_soft_max_back_inplace.restype = ctypes.POINTER(ggml_tensor)


# // rotary position embedding
# // if mode & 1 == 1, skip n_past elements
# // if mode & 2 == 1, GPT-NeoX style
# // if mode & 4 == 1, ChatGLM style
# // TODO: avoid creating a new tensor every time
# GGML_API struct ggml_tensor * ggml_rope(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past,
#         int                   n_dims,
#         int                   mode,
#         int                   n_ctx);
def ggml_rope(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
    n_dims: Union[ctypes.c_int, int],
    mode: Union[ctypes.c_int, int],
    n_ctx: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_rope(ctx, a, n_past, n_dims, mode, n_ctx)


lib.ggml_rope.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
lib.ggml_rope.restype = ctypes.POINTER(ggml_tensor)


# // in-place, returns view(a)
# GGML_API struct ggml_tensor * ggml_rope_inplace(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past,
#         int                   n_dims,
#         int                   mode,
#         int                   n_ctx);
def ggml_rope_inplace(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
    n_dims: Union[ctypes.c_int, int],
    mode: Union[ctypes.c_int, int],
    n_ctx: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_rope_inplace(ctx, a, n_past, n_dims, mode, n_ctx)


lib.ggml_rope_inplace.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
lib.ggml_rope_inplace.restype = ctypes.POINTER(ggml_tensor)


# // rotary position embedding backward, i.e compute dx from dy
# // a - dy
# GGML_API struct ggml_tensor * ggml_rope_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past,
#         int                   n_dims,
#         int                   mode);
def ggml_rope_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
    n_dims: Union[ctypes.c_int, int],
    mode: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_rope_back(ctx, a, n_past, n_dims, mode)


lib.ggml_rope_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
lib.ggml_rope_back.restype = ctypes.POINTER(ggml_tensor)


# // alibi position embedding
# // in-place, returns view(a)
# struct ggml_tensor * ggml_alibi(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   n_past,
#         int                   n_head,
#         float                 bias_max);
def ggml_alibi(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    n_past: Union[ctypes.c_int, int],
    n_head: Union[ctypes.c_int, int],
    bias_max: Union[ctypes.c_float, float],
) -> ggml_tensor_p:  
    return lib.ggml_alibi(ctx, a, n_past, n_head, bias_max)


lib.ggml_alibi.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_float,
]
lib.ggml_alibi.restype = ctypes.POINTER(ggml_tensor)


# // clamp
# // in-place, returns view(a)
# struct ggml_tensor * ggml_clamp(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         float                 min,
#         float                 max);
def ggml_clamp(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    min: Union[ctypes.c_float, float],
    max: Union[ctypes.c_float, float],
) -> ggml_tensor_p:
    return lib.ggml_clamp(ctx, a, min, max)


lib.ggml_clamp.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_float,
    ctypes.c_float,
]
lib.ggml_clamp.restype = ctypes.POINTER(ggml_tensor)


# // padding = half
# // TODO: we don't support extra parameters for now
# //       that's why we are hard-coding the stride, padding, and dilation
# //       not great ..
# // example:
# // a:      3   80  768    1
# // b:   3000   80    1    1
# // res: 3000  768    1    1
# // used in whisper
def ggml_conv_1d_s1_ph(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_conv_1d_s1_ph(ctx, a, b)


lib.ggml_conv_1d_s1_ph.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_conv_1d_s1_ph.restype = ctypes.POINTER(ggml_tensor)


# // used in whisper
# GGML_API struct ggml_tensor * ggml_conv_1d_s2_ph(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_conv_1d_s2_ph(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_conv_1d_s2_ph(ctx, a, b)


lib.ggml_conv_1d_s2_ph.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_conv_1d_s2_ph.restype = ctypes.POINTER(ggml_tensor)


# // kernel size is a->ne[0] x a->ne[1]
# // stride is equal to kernel size
# // padding is zero
# // example:
# // a:     16   16    3  768
# // b:   1024 1024    3    1
# // res:   64   64  768    1
# // used in sam
# GGML_API struct ggml_tensor * ggml_conv_2d_sk_p0(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b);
def ggml_conv_2d_sk_p0(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:
    return lib.ggml_conv_2d_sk_p0(ctx, a, b)


lib.ggml_conv_2d_sk_p0.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_conv_2d_sk_p0.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_flash_attn(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * q,
#         struct ggml_tensor  * k,
#         struct ggml_tensor  * v,
#         bool                  masked);
def ggml_flash_attn(
    ctx: ggml_context_p,
    q: ggml_tensor_p,  
    k: ggml_tensor_p,  
    v: ggml_tensor_p,  
    masked: Union[ctypes.c_bool, bool],
) -> ggml_tensor_p:  
    return lib.ggml_flash_attn(ctx, q, k, v, masked)


lib.ggml_flash_attn.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_bool,
]
lib.ggml_flash_attn.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_flash_attn_back(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * q,
#         struct ggml_tensor  * k,
#         struct ggml_tensor  * v,
#         struct ggml_tensor  * d,
#         bool                  masked);
def ggml_flash_attn_back(
    ctx: ggml_context_p,
    q: ggml_tensor_p,  
    k: ggml_tensor_p,  
    v: ggml_tensor_p,  
    d: ggml_tensor_p,  
    masked: Union[ctypes.c_bool, bool],
) -> ggml_tensor_p:  
    return lib.ggml_flash_attn_back(ctx, q, k, v, d, masked)


lib.ggml_flash_attn_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.c_bool,
]
lib.ggml_flash_attn_back.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_flash_ff(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         struct ggml_tensor  * b0,
#         struct ggml_tensor  * b1,
#         struct ggml_tensor  * c0,
#         struct ggml_tensor  * c1);
def ggml_flash_ff(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b0: ggml_tensor_p,  
    b1: ggml_tensor_p,  
    c0: ggml_tensor_p,  
    c1: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_flash_ff(ctx, a, b0, b1, c0, c1)


lib.ggml_flash_ff.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_flash_ff.restype = ctypes.POINTER(ggml_tensor)


# // partition into non-overlapping windows with padding if needed
# // example:
# // a:   768   64   64    1
# // w:    14
# // res: 768   14   14    25
# // used in sam
# GGML_API struct ggml_tensor * ggml_win_part(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   w);
def ggml_win_part(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    w: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_win_part(ctx, a, w)


lib.ggml_win_part.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
]
lib.ggml_win_part.restype = ctypes.POINTER(ggml_tensor)


# // reverse of ggml_win_part
# // used in sam
# GGML_API struct ggml_tensor * ggml_win_unpart(
#         struct ggml_context * ctx,
#         struct ggml_tensor  * a,
#         int                   w0,
#         int                   h0,
#         int                   w);
def ggml_win_unpart(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    w0: Union[ctypes.c_int, int],
    h0: Union[ctypes.c_int, int],
    w: Union[ctypes.c_int, int],
) -> ggml_tensor_p:  
    return lib.ggml_win_unpart(ctx, a, w0, h0, w)


lib.ggml_win_unpart.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
lib.ggml_win_unpart.restype = ctypes.POINTER(ggml_tensor)

# // custom operators

# typedef void (*ggml_unary_op_f32_t)(const int, float *, const float *);
ggml_unary_op_f32_t = ctypes.CFUNCTYPE(
    None, ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
)

# typedef void (*ggml_binary_op_f32_t)(const int, float *, const float *, const float *);
ggml_binary_op_f32_t = ctypes.CFUNCTYPE(
    None,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
)

# typedef void (*ggml_custom1_op_f32_t)(struct ggml_tensor *, const struct ggml_tensor *);
ggml_custom1_op_f32_t = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(ggml_tensor), ctypes.POINTER(ggml_tensor)
)

# typedef void (*ggml_custom2_op_f32_t)(struct ggml_tensor *, const struct ggml_tensor *, const struct ggml_tensor *);
ggml_custom2_op_f32_t = ctypes.CFUNCTYPE(
    None,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
)

# typedef void (*ggml_custom3_op_f32_t)(struct ggml_tensor *, const struct ggml_tensor *, const struct ggml_tensor *, const struct ggml_tensor *);
ggml_custom3_op_f32_t = ctypes.CFUNCTYPE(
    None,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
)

# GGML_API struct ggml_tensor * ggml_map_unary_f32(
#         struct ggml_context        * ctx,
#         struct ggml_tensor         * a,
#                ggml_unary_op_f32_t   fun);
def ggml_map_unary_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:  
    return lib.ggml_map_unary_f32(ctx, a, fun)


lib.ggml_map_unary_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ggml_unary_op_f32_t,
]
lib.ggml_map_unary_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_unary_inplace_f32(
#         struct ggml_context        * ctx,
#         struct ggml_tensor         * a,
#                 ggml_unary_op_f32_t   fun);
def ggml_map_unary_inplace_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_unary_inplace_f32(ctx, a, fun)

lib.ggml_map_unary_inplace_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ggml_unary_op_f32_t,
]
lib.ggml_map_unary_inplace_f32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_map_binary_f32(
#         struct ggml_context         * ctx,
#         struct ggml_tensor          * a,
#         struct ggml_tensor          * b,
#                ggml_binary_op_f32_t   fun);
def ggml_map_binary_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:  
    return lib.ggml_map_binary_f32(ctx, a, b, fun)


lib.ggml_map_binary_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_binary_op_f32_t,
]
lib.ggml_map_binary_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_binary_inplace_f32(
#         struct ggml_context         * ctx,
#         struct ggml_tensor          * a,
#         struct ggml_tensor          * b,
#                 ggml_binary_op_f32_t   fun);
def ggml_map_binary_inplace_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    b: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_binary_inplace_f32(ctx, a, b, fun)

lib.ggml_map_binary_inplace_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_binary_op_f32_t,
]
lib.ggml_map_binary_inplace_f32.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_map_custom1_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#                 ggml_custom1_op_f32_t   fun);
def ggml_map_custom1_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom1_f32(ctx, a, fun)

lib.ggml_map_custom1_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ggml_custom1_op_f32_t,
]
lib.ggml_map_custom1_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_custom1_inplace_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#                 ggml_custom1_op_f32_t   fun);
def ggml_map_custom1_inplace_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    fun: "ctypes._CFuncPtr" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom1_inplace_f32(ctx, a, fun)

lib.ggml_map_custom1_inplace_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ggml_custom1_op_f32_t,
]
lib.ggml_map_custom1_inplace_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_custom2_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#         struct ggml_tensor           * b,
#                 ggml_custom2_op_f32_t   fun);
def ggml_map_custom2_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    b: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom2_f32(ctx, a, b, fun)

lib.ggml_map_custom2_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_custom2_op_f32_t,
]
lib.ggml_map_custom2_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_custom2_inplace_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#         struct ggml_tensor           * b,
#                 ggml_custom2_op_f32_t   fun);
def ggml_map_custom2_inplace_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    b: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom2_inplace_f32(ctx, a, b, fun)

lib.ggml_map_custom2_inplace_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_custom2_op_f32_t,
]
lib.ggml_map_custom2_inplace_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_custom3_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#         struct ggml_tensor           * b,
#         struct ggml_tensor           * c,
#                 ggml_custom3_op_f32_t   fun);
def ggml_map_custom3_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    b: ggml_tensor_p,
    c: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom3_f32(ctx, a, b, c, fun)

lib.ggml_map_custom3_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_custom3_op_f32_t,
]
lib.ggml_map_custom3_f32.restype = ctypes.POINTER(ggml_tensor)

# GGML_API struct ggml_tensor * ggml_map_custom3_inplace_f32(
#         struct ggml_context          * ctx,
#         struct ggml_tensor           * a,
#         struct ggml_tensor           * b,
#         struct ggml_tensor           * c,
#                 ggml_custom3_op_f32_t   fun);
def ggml_map_custom3_inplace_f32(
    ctx: ggml_context_p,
    a: ggml_tensor_p,
    b: ggml_tensor_p,
    c: ggml_tensor_p,
    fun: "ctypes._FuncPointer" # type: ignore
) -> ggml_tensor_p:
    return lib.ggml_map_custom3_inplace_f32(ctx, a, b, c, fun)

lib.ggml_map_custom3_inplace_f32.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ggml_custom3_op_f32_t,
]
lib.ggml_map_custom3_inplace_f32.restype = ctypes.POINTER(ggml_tensor)

# // loss function


# GGML_API struct ggml_tensor * ggml_cross_entropy_loss(
#         struct ggml_context         * ctx,
#         struct ggml_tensor          * a,
#         struct ggml_tensor          * b);
def ggml_cross_entropy_loss(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_cross_entropy_loss(ctx, a, b)


lib.ggml_cross_entropy_loss.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_cross_entropy_loss.restype = ctypes.POINTER(ggml_tensor)


# GGML_API struct ggml_tensor * ggml_cross_entropy_loss_back(
#         struct ggml_context         * ctx,
#         struct ggml_tensor          * a,
#         struct ggml_tensor          * b,
#         struct ggml_tensor          * c);
def ggml_cross_entropy_loss_back(
    ctx: ggml_context_p,
    a: ggml_tensor_p,  
    b: ggml_tensor_p,  
    c: ggml_tensor_p,  
) -> ggml_tensor_p:  
    return lib.ggml_cross_entropy_loss_back(ctx, a, b, c)


lib.ggml_cross_entropy_loss_back.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_cross_entropy_loss_back.restype = ctypes.POINTER(ggml_tensor)

# //
# // automatic differentiation
# //

# GGML_API void ggml_set_param(
#         struct ggml_context * ctx,
#         struct ggml_tensor * tensor);
def ggml_set_param(
    ctx: ggml_context_p, tensor: ggml_tensor_p  
):
    return lib.ggml_set_param(ctx, tensor)


lib.ggml_set_param.argtypes = [ggml_context_p, ctypes.POINTER(ggml_tensor)]
lib.ggml_set_param.restype = None


# GGML_API void ggml_build_forward_expand(struct ggml_cgraph * cgraph, struct ggml_tensor * tensor);
def ggml_build_forward_expand(
    cgraph: ggml_cgraph_p,  
    tensor: ggml_tensor_p,  
):
    """Add a tensor to the forward computation graph. This is used to
    compute and save the value of the tensor.

    Parameters:
        cgraph: The graph.
        tensor: The tensor."""
    return lib.ggml_build_forward_expand(cgraph, tensor)


lib.ggml_build_forward_expand.argtypes = [
    ctypes.POINTER(ggml_cgraph),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_build_forward_expand.restype = None


# GGML_API struct ggml_cgraph ggml_build_forward (struct ggml_tensor * tensor);
def ggml_build_forward(
    tensor: ggml_tensor_p,  
) -> ggml_cgraph:
    """Build the forward computation graph.
    
    Parameters:
        tensor: The tensor.

    Returns:
        The graph."""
    return lib.ggml_build_forward(tensor)


lib.ggml_build_forward.argtypes = [ctypes.POINTER(ggml_tensor)]
lib.ggml_build_forward.restype = ggml_cgraph


# GGML_API struct ggml_cgraph ggml_build_backward(struct ggml_context * ctx, struct ggml_cgraph * gf, bool keep);
def ggml_build_backward(
    ctx: ggml_context_p,
    gf: ggml_cgraph_p,  
    keep: Union[ctypes.c_bool, bool],
) -> ggml_cgraph:
    return lib.ggml_build_backward(ctx, gf, keep)


lib.ggml_build_backward.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_cgraph),
    ctypes.c_bool,
]
lib.ggml_build_backward.restype = ggml_cgraph


# GGML_API void ggml_graph_compute(struct ggml_context * ctx, struct ggml_cgraph * cgraph);
def ggml_graph_compute(
    ctx: ggml_context_p, cgraph: ggml_cgraph_p
):
    """Compute the graph.
    
    Parameters:
        ctx: The context.
        cgraph: The graph."""
    return lib.ggml_graph_compute(ctx, cgraph)


lib.ggml_graph_compute.argtypes = [ggml_context_p, ctypes.POINTER(ggml_cgraph)]
lib.ggml_graph_compute.restype = None


# GGML_API void ggml_graph_reset  (struct ggml_cgraph * cgraph);
def ggml_graph_reset(
    cgraph: ggml_cgraph_p
):
    """Reset the graph.

    Parameters:
        cgraph: The graph."""
    return lib.ggml_graph_reset(cgraph)


lib.ggml_graph_reset.argtypes = [ctypes.POINTER(ggml_cgraph)]
lib.ggml_graph_reset.restype = None


# GGML_API struct ggml_tensor * ggml_graph_get_tensor(struct ggml_cgraph * cgraph, const char * name);
def ggml_graph_get_tensor(
    cgraph: ggml_cgraph_p,  
    name: bytes,
) -> ggml_tensor_p:
    """Get a tensor from the graph by name.
    
    Parameters:
        cgraph: The graph.
        name: The name of the tensor.

    Returns:
        The tensor."""
    return lib.ggml_graph_get_tensor(cgraph, name)


lib.ggml_graph_get_tensor.argtypes = [
    ctypes.POINTER(ggml_cgraph),
    ctypes.c_char_p,
]
lib.ggml_graph_get_tensor.restype = ctypes.POINTER(ggml_tensor)


# GGML_API void               ggml_graph_export(const struct ggml_cgraph * cgraph, const char * fname);
def ggml_graph_export(
    cgraph: ggml_cgraph_p,  
    fname: bytes,
):
    return lib.ggml_graph_export(cgraph, fname)


lib.ggml_graph_export.argtypes = [
    ctypes.POINTER(ggml_cgraph),
    ctypes.c_char_p,
]
lib.ggml_graph_export.restype = None


# GGML_API struct ggml_cgraph ggml_graph_import(const char * fname, struct ggml_context ** ctx_data, struct ggml_context ** ctx_eval);
def ggml_graph_import(
    fname: bytes,
    ctx_data: "ctypes._Pointer[ggml_context_p]", # type: ignore
    ctx_eval: "ctypes._Pointer[ggml_context_p]", # type: ignore
) -> ggml_cgraph:
    return lib.ggml_graph_import(fname, ctx_data, ctx_eval)


lib.ggml_graph_import.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(ggml_context_p),
    ctypes.POINTER(ggml_context_p),
]
lib.ggml_graph_import.restype = ggml_cgraph


# // print info and performance information for the graph
# GGML_API void ggml_graph_print(const struct ggml_cgraph * cgraph);
def ggml_graph_print(
    cgraph: ggml_cgraph_p,  
):
    return lib.ggml_graph_print(cgraph)


lib.ggml_graph_print.argtypes = [ctypes.POINTER(ggml_cgraph)]
lib.ggml_graph_print.restype = None


# // dump the graph into a file using the dot format
# GGML_API void ggml_graph_dump_dot(const struct ggml_cgraph * gb, const struct ggml_cgraph * gf, const char * filename);
def ggml_graph_dump_dot(
    gb: ggml_cgraph_p,  
    gf: ggml_cgraph_p,  
    filename: bytes,
):
    return lib.ggml_graph_dump_dot(gb, gf, filename)


lib.ggml_graph_dump_dot.argtypes = [
    ctypes.POINTER(ggml_cgraph),
    ctypes.POINTER(ggml_cgraph),
    ctypes.c_char_p,
]
lib.ggml_graph_dump_dot.restype = None


# //
# // optimization
# //

# // optimization methods
# enum ggml_opt_type {
#     GGML_OPT_ADAM,
#     GGML_OPT_LBFGS,
# };
GGML_OPT_ADAM = 0
GGML_OPT_LBFGS = 1

# // linesearch methods
# enum ggml_linesearch {
#     GGML_LINESEARCH_DEFAULT = 1,

#     GGML_LINESEARCH_BACKTRACKING_ARMIJO       = 0,
#     GGML_LINESEARCH_BACKTRACKING_WOLFE        = 1,
#     GGML_LINESEARCH_BACKTRACKING_STRONG_WOLFE = 2,
# };
GGML_LINESEARCH_DEFAULT = 1
GGML_LINESEARCH_BACKTRACKING_ARMIJO = 0
GGML_LINESEARCH_BACKTRACKING_WOLFE = 1
GGML_LINESEARCH_BACKTRACKING_STRONG_WOLFE = 2

# // optimization return values
# enum ggml_opt_result {
#     GGML_OPT_OK = 0,
#     GGML_OPT_DID_NOT_CONVERGE,
#     GGML_OPT_NO_CONTEXT,
#     GGML_OPT_INVALID_WOLFE,
#     GGML_OPT_FAIL,

#     GGML_LINESEARCH_FAIL = -128,
#     GGML_LINESEARCH_MINIMUM_STEP,
#     GGML_LINESEARCH_MAXIMUM_STEP,
#     GGML_LINESEARCH_MAXIMUM_ITERATIONS,
#     GGML_LINESEARCH_INVALID_PARAMETERS,
# };
GGML_OPT_OK = 0
GGML_OPT_DID_NOT_CONVERGE = 1
GGML_OPT_NO_CONTEXT = 2
GGML_OPT_INVALID_WOLFE = 3
GGML_OPT_FAIL = 4
GGML_LINESEARCH_FAIL = -128
GGML_LINESEARCH_MINIMUM_STEP = -127
GGML_LINESEARCH_MAXIMUM_STEP = -126
GGML_LINESEARCH_MAXIMUM_ITERATIONS = -125
GGML_LINESEARCH_INVALID_PARAMETERS = -124


# // optimization parameters
# //
# //   see ggml.c (ggml_opt_default_params) for default values
# //
# struct ggml_opt_params {
#     enum ggml_opt_type type;

#     int n_threads;

#     // delta-based convergence test
#     //
#     //   if past == 0 - disabled
#     //   if past > 0:
#     //     stop if |f(x) - f(x_past)| < delta * max(1, |f(x)|)
#     //
#     int past;
#     float delta;

#     // maximum number of iterations without improvement
#     //
#     //   if 0 - disabled
#     //   if > 0:
#     //     assume convergence if no cost improvement in this number of iterations
#     //
#     int max_no_improvement;

#     bool print_forward_graph;
#     bool print_backward_graph;

#     // ADAM parameters
#     struct {
#         int n_iter;

#         float sched; // schedule multiplier (fixed, decay or warmup)
#         float decay; // weight decay for AdamW, use 0.0f to disable
#         float alpha; // learning rate
#         float beta1;
#         float beta2;
#         float eps;   // epsilon for numerical stability
#         float eps_f; // epsilon for convergence test
#         float eps_g; // epsilon for convergence test
#     } adam;

#     // LBFGS parameters
#     struct {
#         int m; // number of corrections to approximate the inv. Hessian
#         int n_iter;
#         int max_linesearch;

#         float eps;      // convergence tolerance
#         float ftol;     // line search tolerance
#         float wolfe;
#         float min_step;
#         float max_step;

#         enum ggml_linesearch linesearch;
#     } lbfgs;
# };


class ggml_opt_params_adam(ctypes.Structure):
    _fields_ = [
        ("n_iter", ctypes.c_int),
        ("sched", ctypes.c_float),
        ("decay", ctypes.c_float),
        ("alpha", ctypes.c_float),
        ("beta1", ctypes.c_float),
        ("beta2", ctypes.c_float),
        ("eps", ctypes.c_float),
        ("eps_f", ctypes.c_float),
        ("eps_g", ctypes.c_float),
    ]


class ggml_opt_params_lbfgs(ctypes.Structure):
    _fields_ = [
        ("m", ctypes.c_int),
        ("n_iter", ctypes.c_int),
        ("max_linesearch", ctypes.c_int),
        ("eps", ctypes.c_float),
        ("ftol", ctypes.c_float),
        ("wolfe", ctypes.c_float),
        ("min_step", ctypes.c_float),
        ("max_step", ctypes.c_float),
        ("linesearch", ctypes.c_int),
    ]


class ggml_opt_params(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("n_threads", ctypes.c_int),
        ("past", ctypes.c_int),
        ("delta", ctypes.c_float),
        ("max_no_improvement", ctypes.c_int),
        ("print_forward_graph", ctypes.c_bool),
        ("print_backward_graph", ctypes.c_bool),
        ("adam", ggml_opt_params_adam),
        ("lbfgs", ggml_opt_params_lbfgs),
    ]


# struct ggml_opt_context {
#     struct ggml_context * ctx;
#     struct ggml_opt_params params;

#     int iter;
#     int64_t nx; // number of parameter elements

#     bool just_initialized;

#     struct {
#         struct ggml_tensor * x;  // view of the parameters
#         struct ggml_tensor * g1; // gradient
#         struct ggml_tensor * g2; // gradient squared
#         struct ggml_tensor * m;  // first moment
#         struct ggml_tensor * v;  // second moment
#         struct ggml_tensor * mh; // first moment hat
#         struct ggml_tensor * vh; // second moment hat
#         struct ggml_tensor * pf; // past function values
#         float fx_best;
#         float fx_prev;
#         int n_no_improvement;
#     } adam;

#     struct {
#         struct ggml_tensor * x;    // current parameters
#         struct ggml_tensor * xp;   // previous parameters
#         struct ggml_tensor * g;    // current gradient
#         struct ggml_tensor * gp;   // previous gradient
#         struct ggml_tensor * d;    // search direction
#         struct ggml_tensor * pf;   // past function values
#         struct ggml_tensor * lmal; // the L-BFGS memory alpha
#         struct ggml_tensor * lmys; // the L-BFGS memory ys
#         struct ggml_tensor * lms;  // the L-BFGS memory s
#         struct ggml_tensor * lmy;  // the L-BFGS memory y
#         float fx_best;
#         float step;
#         int j;
#         int k;
#         int end;
#         int n_no_improvement;
#     } lbfgs;
# };


class ggml_opt_context_adam(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.POINTER(ggml_tensor)),
        ("g1", ctypes.POINTER(ggml_tensor)),
        ("g2", ctypes.POINTER(ggml_tensor)),
        ("m", ctypes.POINTER(ggml_tensor)),
        ("v", ctypes.POINTER(ggml_tensor)),
        ("mh", ctypes.POINTER(ggml_tensor)),
        ("vh", ctypes.POINTER(ggml_tensor)),
        ("pf", ctypes.POINTER(ggml_tensor)),
        ("fx_best", ctypes.c_float),
        ("fx_prev", ctypes.c_float),
        ("n_no_improvement", ctypes.c_int),
    ]


class ggml_opt_context_lbfgs(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.POINTER(ggml_tensor)),
        ("xp", ctypes.POINTER(ggml_tensor)),
        ("g", ctypes.POINTER(ggml_tensor)),
        ("gp", ctypes.POINTER(ggml_tensor)),
        ("d", ctypes.POINTER(ggml_tensor)),
        ("pf", ctypes.POINTER(ggml_tensor)),
        ("lmal", ctypes.POINTER(ggml_tensor)),
        ("lmys", ctypes.POINTER(ggml_tensor)),
        ("lms", ctypes.POINTER(ggml_tensor)),
        ("lmy", ctypes.POINTER(ggml_tensor)),
        ("fx_best", ctypes.c_float),
        ("step", ctypes.c_float),
        ("j", ctypes.c_int),
        ("k", ctypes.c_int),
        ("end", ctypes.c_int),
        ("n_no_improvement", ctypes.c_int),
    ]


class ggml_opt_context(ctypes.Structure):
    _fields_ = [
        ("ctx", ggml_context_p),
        ("params", ggml_opt_params),
        ("iter", ctypes.c_int),
        ("nx", ctypes.c_int64),
        ("just_initialized", ctypes.c_bool),
        ("adam", ggml_opt_context_adam),
        ("lbfgs", ggml_opt_context_lbfgs),
    ]


# GGML_API struct ggml_opt_params ggml_opt_default_params(enum ggml_opt_type type);
def ggml_opt_default_params(type: Union[ctypes.c_int, bool]) -> ggml_opt_params:
    return lib.ggml_opt_default_params(type)


lib.ggml_opt_default_params.argtypes = [ctypes.c_int]
lib.ggml_opt_default_params.restype = ggml_opt_params


# // optimize the function defined by the tensor f
# GGML_API enum ggml_opt_result ggml_opt(
#         struct ggml_context * ctx,
#         struct ggml_opt_params params,
#         struct ggml_tensor * f);
def ggml_opt(
    ctx: ggml_context_p,
    params: ggml_opt_params,
    f: ggml_tensor_p,
) -> int:
    return lib.ggml_opt(ctx, params, f)


lib.ggml_opt.argtypes = [ggml_context_p, ggml_opt_params, ctypes.POINTER(ggml_tensor)]
lib.ggml_opt.restype = ctypes.c_int


# // initialize optimizer context
# GGML_API void ggml_opt_init(
#         struct ggml_context * ctx,
#         struct ggml_opt_context * opt,
#         struct ggml_opt_params params,
#         int64_t nx);
def ggml_opt_init(
    ctx: ggml_context_p,
    opt: "ctypes._Pointer[ggml_opt_context]",  # type: ignore
    params: ggml_opt_params,
    nx: Union[ctypes.c_int64, int],
):
    return lib.ggml_opt_init(ctx, opt, params, nx)


lib.ggml_opt_init.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_opt_context),
    ggml_opt_params,
    ctypes.c_int64,
]
lib.ggml_opt_init.restype = None


# // continue optimizing the function defined by the tensor f
# GGML_API enum ggml_opt_result ggml_opt_resume(
#         struct ggml_context * ctx,
#         struct ggml_opt_context * opt,
#         struct ggml_tensor * f);
def ggml_opt_resume(
    ctx: ggml_context_p,
    opt: "ctypes._Pointer[ggml_opt_context]",  # type: ignore
    f: ggml_tensor_p,
) -> int:
    return lib.ggml_opt_resume(ctx, opt, f)


lib.ggml_opt_resume.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_opt_context),
    ctypes.POINTER(ggml_tensor),
]
lib.ggml_opt_resume.restype = ctypes.c_int


# // continue optimizing the function defined by the tensor f
# GGML_API enum ggml_opt_result ggml_opt_resume_g(
#         struct ggml_context * ctx,
#         struct ggml_opt_context * opt,
#         struct ggml_tensor * f,
#         struct ggml_cgraph * gf,
#         struct ggml_cgraph * gb);
def ggml_opt_resume_g(
    ctx: ggml_context_p,
    opt: "ctypes._Pointer[ggml_opt_context]", # type: ignore
    f: ggml_tensor_p,
    gf: ggml_cgraph_p,
    gb: ggml_cgraph_p,
) -> int:
    return lib.ggml_opt_resume_g(ctx, opt, f, gf, gb)


lib.ggml_opt_resume_g.argtypes = [
    ggml_context_p,
    ctypes.POINTER(ggml_opt_context),
    ctypes.POINTER(ggml_tensor),
    ctypes.POINTER(ggml_cgraph),
    ctypes.POINTER(ggml_cgraph),
]
lib.ggml_opt_resume_g.restype = ctypes.c_int


# //
# // quantization
# //


# GGML_API size_t ggml_quantize_q4_0(const float * src, void * dst, int n, int k, int64_t * hist);
def ggml_quantize_q4_0(
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    n: Union[ctypes.c_int, int],
    k: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_q4_0(src, dst, n, k, hist)


lib.ggml_quantize_q4_0.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_q4_0.restype = ctypes.c_size_t


# GGML_API size_t ggml_quantize_q4_1(const float * src, void * dst, int n, int k, int64_t * hist);
def ggml_quantize_q4_1(
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    n: Union[ctypes.c_int, int],
    k: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_q4_1(src, dst, n, k, hist)


lib.ggml_quantize_q4_1.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_q4_1.restype = ctypes.c_size_t


# GGML_API size_t ggml_quantize_q5_0(const float * src, void * dst, int n, int k, int64_t * hist);
def ggml_quantize_q5_0(
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    n: Union[ctypes.c_int, int],
    k: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_q5_0(src, dst, n, k, hist)


lib.ggml_quantize_q5_0.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_q5_0.restype = ctypes.c_size_t


# GGML_API size_t ggml_quantize_q5_1(const float * src, void * dst, int n, int k, int64_t * hist);
def ggml_quantize_q5_1(
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    n: Union[ctypes.c_int, int],
    k: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_q5_1(src, dst, n, k, hist)


lib.ggml_quantize_q5_1.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_q5_1.restype = ctypes.c_size_t


# GGML_API size_t ggml_quantize_q8_0(const float * src, void * dst, int n, int k, int64_t * hist);
def ggml_quantize_q8_0(
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    n: Union[ctypes.c_int, int],
    k: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_q8_0(src, dst, n, k, hist)


lib.ggml_quantize_q8_0.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_q8_0.restype = ctypes.c_size_t


# GGML_API size_t ggml_quantize_chunk(enum ggml_type type, const float * src, void * dst, int start, int n, int64_t * hist);
def ggml_quantize_chunk(
    type: Union[ctypes.c_int, int],
    src,  # type: ctypes.Array[ctypes.c_float] 
    dst: ctypes.c_void_p,
    start: Union[ctypes.c_int, int],
    n: Union[ctypes.c_int, int],
    hist,  # type: ctypes.Array[ctypes.c_int64] 
) -> int:
    return lib.ggml_quantize_chunk(type, src, dst, start, n, hist)


lib.ggml_quantize_chunk.argtypes = [
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int64),
]
lib.ggml_quantize_chunk.restype = ctypes.c_size_t

# //
# // system info
# //


# GGML_API int ggml_cpu_has_avx        (void);
def ggml_cpu_has_avx() -> int:
    return lib.ggml_cpu_has_avx()


lib.ggml_cpu_has_avx.argtypes = []
lib.ggml_cpu_has_avx.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_avx2       (void);
def ggml_cpu_has_avx2() -> int:
    return lib.ggml_cpu_has_avx2()


lib.ggml_cpu_has_avx2.argtypes = []
lib.ggml_cpu_has_avx2.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_avx512     (void);
def ggml_cpu_has_avx512() -> int:
    return lib.ggml_cpu_has_avx512()


lib.ggml_cpu_has_avx512.argtypes = []
lib.ggml_cpu_has_avx512.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_avx512_vbmi(void);
def ggml_cpu_has_avx512_vbmi() -> int:
    return lib.ggml_cpu_has_avx512_vbmi()


lib.ggml_cpu_has_avx512_vbmi.argtypes = []
lib.ggml_cpu_has_avx512_vbmi.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_avx512_vnni(void);
def ggml_cpu_has_avx512_vnni() -> int:
    return lib.ggml_cpu_has_avx512_vnni()


lib.ggml_cpu_has_avx512_vnni.argtypes = []
lib.ggml_cpu_has_avx512_vnni.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_fma        (void);
def ggml_cpu_has_fma() -> int:
    return lib.ggml_cpu_has_fma()


lib.ggml_cpu_has_fma.argtypes = []
lib.ggml_cpu_has_fma.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_neon       (void);
def ggml_cpu_has_neon() -> int:
    return lib.ggml_cpu_has_neon()


lib.ggml_cpu_has_neon.argtypes = []
lib.ggml_cpu_has_neon.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_arm_fma    (void);
def ggml_cpu_has_arm_fma() -> int:
    return lib.ggml_cpu_has_arm_fma()


lib.ggml_cpu_has_arm_fma.argtypes = []
lib.ggml_cpu_has_arm_fma.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_f16c       (void);
def ggml_cpu_has_f16c() -> int:
    return lib.ggml_cpu_has_f16c()


lib.ggml_cpu_has_f16c.argtypes = []
lib.ggml_cpu_has_f16c.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_fp16_va    (void);
def ggml_cpu_has_fp16_va() -> int:
    return lib.ggml_cpu_has_fp16_va()


lib.ggml_cpu_has_fp16_va.argtypes = []
lib.ggml_cpu_has_fp16_va.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_wasm_simd  (void);
def ggml_cpu_has_wasm_simd() -> int:
    return lib.ggml_cpu_has_wasm_simd()


lib.ggml_cpu_has_wasm_simd.argtypes = []
lib.ggml_cpu_has_wasm_simd.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_blas       (void);
def ggml_cpu_has_blas() -> int:
    return lib.ggml_cpu_has_blas()


lib.ggml_cpu_has_blas.argtypes = []
lib.ggml_cpu_has_blas.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_cublas     (void);
def ggml_cpu_has_cublas() -> int:
    return lib.ggml_cpu_has_cublas()


lib.ggml_cpu_has_cublas.argtypes = []
lib.ggml_cpu_has_cublas.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_clblast    (void);
def ggml_cpu_has_clblast() -> int:
    return lib.ggml_cpu_has_clblast()


lib.ggml_cpu_has_clblast.argtypes = []
lib.ggml_cpu_has_clblast.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_gpublas    (void);
def ggml_cpu_has_gpublas() -> int:
    return lib.ggml_cpu_has_gpublas()


lib.ggml_cpu_has_gpublas.argtypes = []
lib.ggml_cpu_has_gpublas.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_sse3       (void);
def ggml_cpu_has_sse3() -> int:
    return lib.ggml_cpu_has_sse3()


lib.ggml_cpu_has_sse3.argtypes = []
lib.ggml_cpu_has_sse3.restype = ctypes.c_int


# GGML_API int ggml_cpu_has_vsx        (void);
def ggml_cpu_has_vsx() -> int:
    return lib.ggml_cpu_has_vsx()


lib.ggml_cpu_has_vsx.argtypes = []
lib.ggml_cpu_has_vsx.restype = ctypes.c_int


#####################################################
# GGML CUDA API
# source: ggml-cuda.h
#####################################################


GGML_USE_CUBLAS = hasattr(lib, "ggml_init_cublas")


GGML_CUDA_MAX_DEVICES = ctypes.c_int(16)


# void * ggml_cuda_host_malloc(size_t size);
def ggml_cuda_host_malloc(
    size: Union[ctypes.c_size_t, int],
) -> Optional[ctypes.c_void_p]:
    return lib.ggml_cuda_host_malloc(size)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_host_malloc.argtypes = [ctypes.c_size_t]
    lib.ggml_cuda_host_malloc.restype = ctypes.c_void_p


# void   ggml_cuda_host_free(void * ptr);
def ggml_cuda_host_free(
    ptr: ctypes.c_void_p,
):
    return lib.ggml_cuda_host_free(ptr)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_host_free.argtypes = [ctypes.c_void_p]
    lib.ggml_cuda_host_free.restype = None


# void   ggml_cuda_transform_tensor(void * data, struct ggml_tensor * tensor);
def ggml_cuda_transform_tensor(
    data: ctypes.c_void_p,
    tensor: ggml_tensor_p,  
):
    return lib.ggml_cuda_transform_tensor(data, tensor)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_transform_tensor.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cuda_transform_tensor.restype = None


# void   ggml_cuda_set_tensor_split(const float * tensor_split);
def ggml_cuda_set_tensor_split(
    tensor_split,  # type: ctypes.Array[ctypes.c_float] 
):
    return lib.ggml_cuda_set_tensor_split(tensor_split)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_set_tensor_split.argtypes = [ctypes.POINTER(ctypes.c_float)]
    lib.ggml_cuda_set_tensor_split.restype = None


# void   ggml_cuda_free_data(struct ggml_tensor * tensor);
def ggml_cuda_free_data(
    tensor: ggml_tensor_p,
):
    return lib.ggml_cuda_free_data(tensor)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_free_data.argtypes = [
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cuda_free_data.restype = None


# void   ggml_cuda_assign_buffers(struct ggml_tensor * tensor);
def ggml_cuda_assign_buffers(
    tensor: ggml_tensor_p,  
):
    return lib.ggml_cuda_assign_buffers(tensor)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_assign_buffers.argtypes = [
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cuda_assign_buffers.restype = None


# void   ggml_cuda_assign_buffers_no_scratch(struct ggml_tensor * tensor);
def ggml_cuda_assign_buffers_no_scratch(
    tensor: ggml_tensor_p,  
):
    return lib.ggml_cuda_assign_buffers_no_scratch(tensor)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_assign_buffers_no_scratch.argtypes = [
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cuda_assign_buffers_no_scratch.restype = None


# void   ggml_cuda_set_main_device(int main_device);
def ggml_cuda_set_main_device(
    main_device: Union[ctypes.c_int, int],
):
    return lib.ggml_cuda_set_main_device(main_device)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_set_main_device.argtypes = [
        ctypes.c_int,
    ]
    lib.ggml_cuda_set_main_device.restype = None


# void   ggml_cuda_set_scratch_size(size_t scratch_size);
def ggml_cuda_set_scratch_size(
    scratch_size: Union[ctypes.c_size_t, int],
):
    return lib.ggml_cuda_set_scratch_size(scratch_size)


if GGML_USE_CUBLAS:
    lib.ggml_cuda_set_scratch_size.argtypes = [
        ctypes.c_size_t,
    ]
    lib.ggml_cuda_set_scratch_size.restype = None


# void   ggml_cuda_free_scratch(void);
def ggml_cuda_free_scratch():
    return lib.ggml_cuda_free_scratch()


if GGML_USE_CUBLAS:
    lib.ggml_cuda_free_scratch.argtypes = []
    lib.ggml_cuda_free_scratch.restype = None


#####################################################
# GGML METAL API
# source: ggml-metal.h
#####################################################


GGML_USE_METAL = hasattr(lib, "ggml_metal_init")


GGML_METAL_MAX_BUFFERS = ctypes.c_int(16)

# struct ggml_metal_context;
ggml_metal_context_p = ctypes.c_void_p


# struct ggml_metal_context * ggml_metal_init(void);
def ggml_metal_init() -> ggml_metal_context_p:
    return lib.ggml_metal_init()


if GGML_USE_METAL:
    lib.ggml_metal_init.argtypes = []
    lib.ggml_metal_init.restype = ggml_metal_context_p

# void ggml_metal_free(struct ggml_metal_context * ctx);


# // creates a mapping between a host memory buffer and a device memory buffer
# // - make sure to map all buffers used in the graph before calling ggml_metal_graph_compute
# // - the mapping is used during computation to determine the arguments of the compute kernels
# // - you don't need to keep the host memory buffer allocated as it is never accessed by Metal
# // - max_size specifies the maximum size of a tensor and is used to create shared views such
# //   that it is guaranteed that the tensor will fit in at least one of the views
# //
# bool ggml_metal_add_buffer(
#         struct ggml_metal_context * ctx,
#                        const char * name,
#                              void * data,
#                            size_t   size,
#                            size_t   max_size);
def ggml_metal_add_buffer(
    ctx: ggml_metal_context_p,
    name: ctypes.c_char_p,
    data: ctypes.c_void_p,
    size: Union[ctypes.c_size_t, int],
    max_size: Union[ctypes.c_size_t, int],
) -> ctypes.c_bool:
    return lib.ggml_metal_add_buffer(ctx, name, data, size, max_size)


if GGML_USE_METAL:
    lib.ggml_metal_add_buffer.argtypes = [
        ggml_metal_context_p,
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_size_t,
    ]
    lib.ggml_metal_add_buffer.restype = ctypes.c_bool


# // get data from the device into host memory
# void ggml_metal_get_tensor(struct ggml_metal_context * ctx, struct ggml_tensor * t);
def ggml_metal_get_tensor(
    ctx: ggml_metal_context_p,
    t: ggml_tensor_p,  
):
    return lib.ggml_metal_get_tensor(ctx, t)


if GGML_USE_METAL:
    lib.ggml_metal_get_tensor.argtypes = [
        ggml_metal_context_p,
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_metal_get_tensor.restype = None


# // same as ggml_graph_compute but uses Metal
# // creates gf->n_threads command buffers in parallel
# void ggml_metal_graph_compute(struct ggml_metal_context * ctx, struct ggml_cgraph * gf);
def ggml_metal_graph_compute(
    ctx: ggml_metal_context_p,
    gf: ggml_cgraph_p,  
):
    return lib.ggml_metal_graph_compute(ctx, gf)


if GGML_USE_METAL:
    lib.ggml_metal_graph_compute.argtypes = [
        ggml_metal_context_p,
        ctypes.POINTER(ggml_cgraph),
    ]
    lib.ggml_metal_graph_compute.restype = None


#####################################################
# GGML OPENCL API
# source: ggml-opencl.h
#####################################################


GGML_USE_CLBLAST = hasattr(lib, "ggml_cl_init")


# void ggml_cl_free_data(const struct ggml_tensor* tensor);
def ggml_cl_free_data(
    tensor: ggml_tensor_p,
):
    return lib.ggml_cl_free_data(tensor)


if GGML_USE_CLBLAST:
    lib.ggml_cl_free_data.argtypes = [
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cl_free_data.restype = None


# void ggml_cl_transform_tensor(void * data, struct ggml_tensor * tensor);
def ggml_cl_transform_tensor(
    data: ctypes.c_void_p,
    tensor: ggml_tensor_p,  
):
    return lib.ggml_cl_transform_tensor(data, tensor)


if GGML_USE_CLBLAST:
    lib.ggml_cl_transform_tensor.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ggml_tensor),
    ]
    lib.ggml_cl_transform_tensor.restype = None
